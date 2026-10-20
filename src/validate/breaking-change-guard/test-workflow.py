#!/usr/bin/env python3

import json
import os
import re
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "pr-validation.yml"
SELF_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "self-pr-validation.yml"
GO_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "go-pr-validation.yml"
GO_ANALYSIS_PATH = REPO_ROOT / ".github" / "workflows" / "go-pr-analysis.yml"
JS_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "js-pr-validation.yml"
FRONTEND_ANALYSIS_PATH = REPO_ROOT / ".github" / "workflows" / "frontend-pr-analysis.yml"
REPORTER_PATH = REPO_ROOT / "src" / "notify" / "pr-validation-reporter" / "action.yml"
SUMMARY_PATH = REPO_ROOT / "src" / "validate" / "pr-checks-summary" / "action.yml"
README_PATH = REPO_ROOT / "src" / "validate" / "breaking-change-guard" / "README.md"

WORKFLOW = WORKFLOW_PATH.read_text(encoding="utf-8")
SELF_WORKFLOW = SELF_WORKFLOW_PATH.read_text(encoding="utf-8")
GO_WORKFLOW = GO_WORKFLOW_PATH.read_text(encoding="utf-8")
GO_ANALYSIS = GO_ANALYSIS_PATH.read_text(encoding="utf-8")
JS_WORKFLOW = JS_WORKFLOW_PATH.read_text(encoding="utf-8")
FRONTEND_ANALYSIS = FRONTEND_ANALYSIS_PATH.read_text(encoding="utf-8")
REPORTER = REPORTER_PATH.read_text(encoding="utf-8")
SUMMARY = SUMMARY_PATH.read_text(encoding="utf-8")
README = README_PATH.read_text(encoding="utf-8")

ACKNOWLEDGEMENT = (
    "Breaking change acknowledged: I understand that this PR intentionally "
    "introduces a breaking change and requires the next release to be a major version."
)

APPROVAL_WORKFLOW_PATH = (
    REPO_ROOT / ".github" / "workflows" / "breaking-change-approval.yml"
)
APPROVAL_WORKFLOW = APPROVAL_WORKFLOW_PATH.read_text(encoding="utf-8")

# Composites the approval gate orchestrates. Each must exist with the action.yml
# + README.md pair the repository requires.
APPROVAL_COMPOSITES = (
    "src/validate/pr-gate-scope",
    "src/validate/environment-protection",
    "src/validate/environment-approvals",
    "src/notify/breaking-change-approval-reporter",
    "src/validate/codeowners-reviewers",
    "src/validate/breaking-change-commits",
)
ENVIRONMENT_PROTECTION = (
    REPO_ROOT / "src" / "validate" / "environment-protection" / "action.yml"
).read_text(encoding="utf-8")
ENVIRONMENT_APPROVALS = (
    REPO_ROOT / "src" / "validate" / "environment-approvals" / "action.yml"
).read_text(encoding="utf-8")

# The mandatory author-acknowledgement guard must stay unconfigurable, which the
# tests below enforce by rejecting any input whose name mentions "breaking" or
# "acknowledgement". The human approval gate is a separate control and is meant to
# be configurable, so its inputs are allowed — by name, one at a time. Adding to
# this set is the deliberate act; forgetting to is a failing test.
APPROVAL_GATE_INPUTS = {
    "enable_breaking_change_approval",
    "breaking_change_scope_rules",
    "breaking_change_additional_scope_rules",
    "breaking_change_force_labels",
    "breaking_change_skip_labels",
    "breaking_change_close_on_rejection",
    "breaking_change_require_protected_environment",
    "breaking_change_approval_reviewers",
    "breaking_change_fallback_reviewers",
    "breaking_change_create_environment",
}


def indentation(line):
    return len(line) - len(line.lstrip(" "))


def extract_step(text, step_name):
    lines = text.splitlines()
    marker = f"- name: {step_name}"
    for start, line in enumerate(lines):
        if line.strip() == marker:
            step_indent = indentation(line)
            break
    else:
        raise AssertionError(f"step not found: {step_name}")

    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if line.strip() and indentation(line) <= step_indent:
            end = index
            break
    return "\n".join(lines[start:end])


def extract_run_body(text, step_name):
    step = extract_step(text, step_name)
    lines = step.splitlines()
    for start, line in enumerate(lines):
        if line.strip() == "run: |":
            run_indent = indentation(line)
            break
    else:
        raise AssertionError(f"run body not found for step: {step_name}")

    body = []
    for line in lines[start + 1 :]:
        if line.strip() and indentation(line) <= run_indent:
            break
        body.append(line)
    return textwrap.dedent("\n".join(body)).rstrip() + "\n"


def extract_job(text, job_id):
    lines = text.splitlines()
    marker = f"  {job_id}:"
    try:
        start = lines.index(marker)
    except ValueError as error:
        raise AssertionError(f"job not found: {job_id}") from error

    end = len(lines)
    for index in range(start + 1, len(lines)):
        if re.fullmatch(r"  [A-Za-z0-9_-]+:", lines[index]):
            end = index
            break
    return "\n".join(lines[start:end])


def extract_top_level_section(text, section_name):
    lines = text.splitlines()
    marker = f"{section_name}:"
    try:
        start = lines.index(marker)
    except ValueError as error:
        raise AssertionError(f"section not found: {section_name}") from error

    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index] and not lines[index].startswith((" ", "\t")):
            end = index
            break
    return "\n".join(lines[start:end])


def extract_mapping_entry(section, key, indent=2):
    lines = section.splitlines()
    marker = f"{' ' * indent}{key}:"
    try:
        start = lines.index(marker)
    except ValueError as error:
        raise AssertionError(f"mapping entry not found: {key}") from error

    end = len(lines)
    entry_pattern = re.compile(rf"^{' ' * indent}[A-Za-z0-9_-]+:$")
    for index in range(start + 1, len(lines)):
        if entry_pattern.fullmatch(lines[index]):
            end = index
            break
    return "\n".join(lines[start:end])


def extract_workflow_call_section(text, section_name):
    lines = text.splitlines()
    start_marker = f"    {section_name}:"
    try:
        start = lines.index(start_marker)
    except ValueError as error:
        raise AssertionError(
            f"workflow_call section not found: {section_name}"
        ) from error

    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if line.strip() and indentation(line) <= 4:
            end = index
            break
    return "\n".join(lines[start:end])


def mapping_keys(section, indent):
    pattern = re.compile(rf"^{' ' * indent}([A-Za-z0-9_-]+):$")
    return [
        match.group(1)
        for line in section.splitlines()
        if (match := pattern.fullmatch(line))
    ]


def execute_body(body, env):
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "github-output"
        controlled_env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": temp_dir,
        }
        controlled_env.update(env)
        controlled_env["GITHUB_OUTPUT"] = str(output_path)
        result = subprocess.run(
            ["bash", "-c", body],
            cwd=temp_dir,
            env=controlled_env,
            text=True,
            capture_output=True,
            check=False,
        )
        output = output_path.read_text(encoding="utf-8") if output_path.exists() else ""
        return result, parse_github_output(output)


def render_reporter(state, **overrides):
    """Render the reporter's comment for one state and return the Markdown.

    Asserting against the composite's source only proves a string exists
    somewhere in it — swapping two states' alerts would keep every string
    present and every assertion green. Running the thing and reading what it
    produced is the only check that ties a state to its own output.
    """
    action = yaml.safe_load(
        (
            REPO_ROOT / "src" / "notify" / "breaking-change-approval-reporter"
            / "action.yml"
        ).read_text(encoding="utf-8")
    )
    # Everything up to the posting is the part that builds the Markdown.
    body = action["runs"]["steps"][0]["run"].split('comment_id=""')[0]

    env = {
        "REPO": "LerianStudio/example",
        "PR_NUMBER": "42",
        "STATE": state,
        "REASON": "rule develop <- '*'",
        "HEAD_SHA": "abc1234567",
        "ACKNOWLEDGED": "false",
        "ACK_LINE": "Breaking change acknowledged: I understand that this PR "
        "intentionally introduces a breaking change and requires the next "
        "release to be a major version.",
        "RUN_URL": "https://github.com/LerianStudio/example/actions/runs/1",
        "REVIEWERS": "team:devops",
        "SERVER_URL": "https://github.com",
        "BADGE_URL": "https://img.shields.io/badge/x-1f6feb",
        "DOCS_URL": "https://example.invalid/docs",
        "APPROVERS": "carol",
        "REJECTERS": "dave",
        "REJECTION_COMMENT": "",
        "CLOSE_ON_REJECTION": "true",
        "LABEL": "breaking-change",
        "ENABLED": "true",
        "GH_TOKEN": "stub",
        # Empty: these fixtures exercise the standalone path, where the
        # composite reads the commits itself and `MOCK_SUBJECTS` feeds the
        # stubbed API. Pass `SUBJECTS` to exercise the forwarded set instead.
        "SUBJECTS": "",
        "MOCK_SUBJECTS": "",
    }
    env.update(overrides)

    with tempfile.TemporaryDirectory() as stub_dir:
        stub = Path(stub_dir) / "gh"
        stub.write_text(
            "#!/usr/bin/env bash\n"
            "case \"$*\" in\n"
            "  *\"/commits\"*) printf '%s\\n'"
            ' "${MOCK_SUBJECTS:-feat(scope)!: a breaking subject}"'
            " 'chore: an ordinary one' ;;\n"
            "  *) exit 1 ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        stub.chmod(0o755)
        env["PATH"] = f"{stub_dir}:{os.environ.get('PATH', '/usr/bin:/bin')}"
        result = subprocess.run(
            ["bash", "-c", body + '\ncat "$body_file"'],
            cwd=stub_dir,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
    if result.returncode != 0:
        raise AssertionError(f"reporter failed for state {state!r}: {result.stderr}")
    return result.stdout


def run_verdict(**overrides):
    """Run the gate's verdict step and return its outputs.

    Asserting that the cancellation branch contains `exit 0` would only prove
    the characters are there. Running it with a recorded rejection in hand is
    what proves the branch actually stops: without the exit, the rejection
    downstream wins and the pull request gets closed.
    """
    workflow = yaml.safe_load(APPROVAL_WORKFLOW)
    step = next(
        s
        for s in workflow["jobs"]["outcome"]["steps"]
        if s.get("name") == "Resolve the verdict"
    )

    env = {
        "GH_TOKEN": "stub",
        "REPO": "LerianStudio/example",
        "HEAD_SHA": "abc123",
        "DETECT_RESULT": "success",
        "REQUEST_RESULT": "success",
        "APPROVAL_RESULT": "success",
        "IN_SCOPE": "true",
        "REASON": "rule develop <- '*'",
        "PR_NUMBER": "42",
        "HAS_BREAKING_CHANGES": "true",
        "DETECTION_SUCCEEDED": "true",
        "APPROVERS": "",
        "REJECTERS": "",
        "API_READABLE": "true",
        "DRY_RUN": "false",
        "LIVE_SHA": "abc123",
        "ALREADY_APPROVED": "false",
        "HEAD_REF": "feat/x",
        "RUN_ID": "100",
        "MOCK_NEWER_RUNS": "0",
        # Production always supplies these; the fixture did not, so the label
        # cleanup expanded them under `set -u` and the step died with
        # `LABEL: unbound variable` after emitting its outputs. Every caller
        # read the outputs and ignored the exit code, so the suite stayed green
        # on a step that had crashed.
        "LABEL": "breaking-change",
        "PENDING_LABEL": "awaiting-breaking-approval",
    }
    env.update(overrides)

    # `MOCK_NEWER_RUNS=N` is shorthand for N newer runs of this workflow, all
    # belonging to this pull request. Pass `MOCK_RUNS_JSON` directly to say
    # something the shorthand cannot — a run of another pull request, or a run
    # from a fork with no `pull_requests` at all.
    if "MOCK_RUNS_JSON" not in env:
        run_id = int(env["RUN_ID"])
        pr_number = int(env["PR_NUMBER"] or 0)
        env["MOCK_RUNS_JSON"] = json.dumps(
            {
                "workflow_runs": [
                    {
                        "id": run_id + 1 + i,
                        "event": "pull_request",
                        "head_sha": env["HEAD_SHA"],
                        "pull_requests": [{"number": pr_number}],
                    }
                    for i in range(int(env["MOCK_NEWER_RUNS"]))
                ]
            }
        )

    with tempfile.TemporaryDirectory() as temp_dir:
        stub = Path(temp_dir) / "gh"
        # The stub runs the real `--jq` against a real payload. Returning the
        # count directly was how the branch-wide query survived a whole round
        # of review: the filter was never executed, so no test could see what
        # it selected. Here the query is the thing under test.
        stub.write_text(
            "#!/usr/bin/env bash\n"
            # Every invocation is recorded. Label behaviour was pinned by
            # grepping the step for its loop, which is how a loop removing the
            # wrong label stayed green — the assertion described the code
            # rather than what it did.
            'printf \'%s\\n\' "$*" >> "$GH_CALLS"\n'
            'jq_query=""\n'
            'prev=""\n'
            'for arg in "$@"; do\n'
            '  [ "$prev" = "--jq" ] && jq_query="$arg"\n'
            '  prev="$arg"\n'
            "done\n"
            'case "$*" in\n'
            '  *headRefOid*) printf \'%s\\n\' "$LIVE_SHA" ;;\n'
            # Only the workflow-scoped URL answers. A query against
            # `actions/runs?branch=` — every workflow on the branch — gets
            # nothing, so a regression to it reads as "no newer run" and fails
            # the supersession cases rather than passing them silently.
            '  *"/actions/workflows/"*"/runs?branch"*)'
            ' printf \'%s\' "$MOCK_RUNS_JSON" | jq -r "$jq_query" ;;\n'
            '  *"actions/runs/"*) printf \'%s\\n\' "4242" ;;\n'
            "  *) exit 1 ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        stub.chmod(0o755)
        output_path = Path(temp_dir) / "github-output"
        output_path.touch()
        calls_path = Path(temp_dir) / "gh-calls"
        calls_path.touch()
        env["GH_CALLS"] = str(calls_path)
        env["GITHUB_OUTPUT"] = str(output_path)
        env["GITHUB_STEP_SUMMARY"] = str(Path(temp_dir) / "summary")
        env["PATH"] = f"{temp_dir}:{os.environ.get('PATH', '/usr/bin:/bin')}"
        result = subprocess.run(
            ["bash", "-c", step["run"]],
            cwd=temp_dir,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        result.gh_calls = calls_path.read_text(encoding="utf-8").splitlines()
        if result.returncode != 0:
            raise AssertionError(
                "the verdict step exited %d:\n%s"
                % (result.returncode, result.stderr.strip())
            )
        return result, parse_github_output(output_path.read_text(encoding="utf-8"))


def run_detect_normalization(**overrides):
    """Run the gate's own normalization step and return its outputs.

    The public `has_breaking_changes` output is this step's value passed
    straight through, so the documented contract — what a caller reads out of
    scope — lives here and nowhere else.
    """
    workflow = yaml.safe_load(APPROVAL_WORKFLOW)
    step = next(
        s
        for s in workflow["jobs"]["detect"]["steps"]
        if s.get("name") == "Normalize detection result"
    )

    env = {
        "IN_SCOPE": "true",
        "SUPPLIED_HAS_BREAKING_CHANGES": "",
        "SUPPLIED_ACKNOWLEDGED": "",
        "COMMITS_OUTCOME": "success",
        "BREAKING_COUNT": "0",
    }
    env.update(overrides)

    # Selection and defaults here, execution in `execute_body` — which already
    # owns the temporary directory, `GITHUB_OUTPUT` and the parsing. This used
    # to carry its own copy of all three.
    _, outputs = execute_body(step["run"], env)
    return outputs


def run_reporter_comment(
    state, existing_body=None, read_fails=False, legacy_ids="", **overrides
):
    """Run the reporter with commenting on, and report what it did to the comment.

    Returns (process, calls) where `calls` lists every `gh` invocation, so a
    test can say whether a PATCH was issued and what body it carried.

    `render_reporter` stops before the comment handling and
    `run_reporter_labels` turns commenting off, so the record-preservation
    path — the one thing standing between a transient API error and every
    approval on the pull request being erased — had no executable coverage at
    all. It was pinned by grepping the composite for its own error message.
    """
    action = yaml.safe_load(
        (
            REPO_ROOT / "src" / "notify" / "breaking-change-approval-reporter"
            / "action.yml"
        ).read_text(encoding="utf-8")
    )
    body = action["runs"]["steps"][0]["run"]

    env = {
        "REPO": "LerianStudio/example",
        "PR_NUMBER": "42",
        "STATE": state,
        "REASON": "rule develop <- '*'",
        "HEAD_SHA": "abc1234567",
        "ACKNOWLEDGED": "true",
        "ACK_LINE": "Breaking change acknowledged: …",
        "SUBJECTS": "",
        "RUN_URL": "https://github.com/LerianStudio/example/actions/runs/1",
        "REVIEWERS": "team:devops",
        "SERVER_URL": "https://github.com",
        "BADGE_URL": "https://img.shields.io/badge/x-1f6feb",
        "DOCS_URL": "https://example.invalid/docs",
        "APPROVERS": "carol",
        "REJECTERS": "",
        "REJECTION_COMMENT": "",
        "CLOSE_ON_REJECTION": "true",
        "LABEL": "breaking-change",
        "PENDING_LABEL": "awaiting-breaking-approval",
        "ENABLED": "true",
        "FINGERPRINT": "",
        "RUN_ID": "1",
        "GH_TOKEN": "stub",
    }
    env.update(overrides)

    with tempfile.TemporaryDirectory() as temp_dir:
        calls = Path(temp_dir) / "calls"
        calls.touch()
        bodies = Path(temp_dir) / "bodies"
        bodies.touch()
        existing = Path(temp_dir) / "existing-body"
        existing.write_text(existing_body or "", encoding="utf-8")

        # `read_fails` is the whole point: the composite must refuse rather
        # than treat an unreadable comment as one holding no records.
        read_arm = (
            "  *\"issues/comments/\"*) exit 1 ;;\n"
            if read_fails
            else f"  *\"issues/comments/\"*) cat '{existing}' ;;\n"
        )
        stub = Path(temp_dir) / "gh"
        stub.write_text(
            "#!/usr/bin/env bash\n"
            f'printf \'%s\\n\' "$*" >> "{calls}"\n'
            # The body goes out as `-F body=@<tmpfile>` and the composite
            # deletes that file on exit, so keep a copy while it still exists.
            'for arg in "$@"; do\n'
            '  case "$arg" in\n'
            f'    body=@*) cat "${{arg#body=@}}" >> "{bodies}" ;;\n'
            "  esac\n"
            "done\n"
            'case "$*" in\n'
            "  *\"pr edit\"*) exit 0 ;;\n"
            "  *\"/commits\"*) printf '%s\\n' 'feat(x)!: breaks' ;;\n"
            # The listing is queried twice with different `--jq`: once for
            # this composite's own comment, once for legacy ones to retire.
            # Answer each by what it asked for.
            "  *\"issues/42/comments\"*)\n"
            '    case "$*" in\n'
            f"      *lerian-breaking-change-guard*) printf '%s\\n' '{legacy_ids}' ;;\n"
            "      *) printf '%s\\n' '7' ;;\n"
            "    esac ;;\n"
            + read_arm
            + "  *) exit 1 ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        stub.chmod(0o755)
        env["PATH"] = f"{temp_dir}:{os.environ.get('PATH', '/usr/bin:/bin')}"
        env["GITHUB_OUTPUT"] = str(Path(temp_dir) / "out")
        env["GITHUB_STEP_SUMMARY"] = str(Path(temp_dir) / "summary")
        Path(env["GITHUB_OUTPUT"]).touch()
        result = subprocess.run(
            ["bash", "-c", body],
            cwd=temp_dir,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        result.posted_body = bodies.read_text(encoding="utf-8")
        return result, calls.read_text(encoding="utf-8").splitlines()


def run_reporter_labels(state, **overrides):
    """Run the reporter end to end and return the `gh pr edit` calls it made.

    `render_reporter` stops before the label block, so asserting on the
    composite's text was the only coverage the lifecycle had — and text cannot
    tell which state made which call. Moving `--add-label "$LABEL"` into the
    `waiting` branch would keep every string in place and break the behaviour.
    """
    action = yaml.safe_load(
        (
            REPO_ROOT / "src" / "notify" / "breaking-change-approval-reporter"
            / "action.yml"
        ).read_text(encoding="utf-8")
    )
    body = action["runs"]["steps"][0]["run"]

    env = {
        "REPO": "LerianStudio/example",
        "PR_NUMBER": "42",
        "STATE": state,
        "REASON": "rule develop <- '*'",
        "HEAD_SHA": "abc1234567",
        "ACKNOWLEDGED": "false",
        "ACK_LINE": "Breaking change acknowledged: …",
        "RUN_URL": "https://github.com/LerianStudio/example/actions/runs/1",
        "REVIEWERS": "team:devops",
        "SERVER_URL": "https://github.com",
        "BADGE_URL": "https://img.shields.io/badge/x-1f6feb",
        "DOCS_URL": "https://example.invalid/docs",
        "APPROVERS": "carol",
        "REJECTERS": "dave",
        "REJECTION_COMMENT": "",
        "CLOSE_ON_REJECTION": "true",
        "LABEL": "breaking-change",
        "PENDING_LABEL": "awaiting-breaking-approval",
        "ENABLED": "false",
        "SUBJECTS": "",
        "FINGERPRINT": "",
        "RUN_ID": "1",
        "GH_TOKEN": "stub",
    }
    env.update(overrides)

    with tempfile.TemporaryDirectory() as temp_dir:
        calls = Path(temp_dir) / "calls"
        calls.touch()
        stub = Path(temp_dir) / "gh"
        stub.write_text(
            "#!/usr/bin/env bash\n"
            'case "$*" in\n'
            "  *\"pr edit\"*)"
            " printf '%s\\n' \"$*\" | grep -oE '(add|remove)-label [a-z-]+'"
            f' >> "{calls}" ;;\n'
            "  *\"/commits\"*) printf '%s\\n' 'feat(x)!: breaks' ;;\n"
            "  *) exit 1 ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        stub.chmod(0o755)
        env["PATH"] = f"{temp_dir}:{os.environ.get('PATH', '/usr/bin:/bin')}"
        env["GITHUB_OUTPUT"] = str(Path(temp_dir) / "out")
        result = subprocess.run(
            ["bash", "-c", body],
            cwd=temp_dir,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise AssertionError(f"reporter failed for {state!r}: {result.stderr}")
        # `set -u` firing inside a command substitution kills the subshell and
        # leaves the script running with exit 0. A fixture missing a variable
        # then reads as "the step made no calls" — a green test on a step that
        # half ran. The exit code cannot see it; stderr can.
        if "unbound variable" in result.stderr:
            raise AssertionError(f"incomplete fixture for {state!r}: {result.stderr}")
        return calls.read_text(encoding="utf-8").split()


def parse_github_output(output):
    values = {}
    for line in output.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


EVENT_BODY = extract_run_body(WORKFLOW, "Validate original event")
NORMALIZE_BODY = extract_run_body(WORKFLOW, "Normalize breaking change result")
ENFORCE_BODY = extract_run_body(WORKFLOW, "Enforce breaking change guard")


class EventValidationTests(unittest.TestCase):
    def valid_event_env(self):
        return {
            "EVENT_NAME": "pull_request",
            "PR_NUMBER": "42",
            "PR_HEAD_REF": "feature/guard",
            "PR_HEAD_SHA": "a" * 40,
            "PR_BASE_REF": "develop",
            "PR_BASE_SHA": "b" * 40,
        }

    def test_pull_request_event_succeeds(self):
        result, _ = execute_body(EVENT_BODY, self.valid_event_env())
        self.assertEqual(0, result.returncode, result.stderr)

    def test_pull_request_target_event_fails(self):
        env = self.valid_event_env()
        env["EVENT_NAME"] = "pull_request_target"
        result, _ = execute_body(EVENT_BODY, env)
        self.assertNotEqual(0, result.returncode)

    def test_workflow_dispatch_event_fails(self):
        env = self.valid_event_env()
        env["EVENT_NAME"] = "workflow_dispatch"
        result, _ = execute_body(EVENT_BODY, env)
        self.assertNotEqual(0, result.returncode)

    def test_pull_request_with_missing_event_data_fails(self):
        env = self.valid_event_env()
        env["PR_HEAD_SHA"] = ""
        result, _ = execute_body(EVENT_BODY, env)
        self.assertNotEqual(0, result.returncode)

    def test_absent_required_variable_fails(self):
        env = self.valid_event_env()
        del env["EVENT_NAME"]
        result, _ = execute_body(EVENT_BODY, env)
        self.assertNotEqual(0, result.returncode)


class NormalizationTests(unittest.TestCase):
    def normalize(self, **overrides):
        env = {
            "EVENT_VALIDATION_OUTCOME": "success",
            "CHECKOUT_OUTCOME": "success",
            "GUARD_OUTCOME": "success",
            "RAW_HAS_BREAKING_CHANGES": "false",
            "RAW_APPROVED": "false",
        }
        env.update(overrides)
        result, output = execute_body(NORMALIZE_BODY, env)
        self.assertEqual(0, result.returncode, result.stderr)
        return output

    def assert_normalized(
        self, output, *, has_breaking, acknowledged, result, detected
    ):
        self.assertEqual(
            {
                "has-breaking-changes": has_breaking,
                "approved": acknowledged,
                "result": result,
                "detection-succeeded": detected,
            },
            output,
        )

    def test_no_breaking_change_succeeds(self):
        output = self.normalize()
        self.assert_normalized(
            output,
            has_breaking="false",
            acknowledged="false",
            result="success",
            detected="true",
        )

    def test_unacknowledged_breaking_change_fails(self):
        output = self.normalize(RAW_HAS_BREAKING_CHANGES="true")
        self.assert_normalized(
            output,
            has_breaking="true",
            acknowledged="false",
            result="failure",
            detected="true",
        )

    def test_exact_author_acknowledgement_succeeds(self):
        output = self.normalize(RAW_HAS_BREAKING_CHANGES="true", RAW_APPROVED="true")
        self.assert_normalized(
            output,
            has_breaking="true",
            acknowledged="true",
            result="success",
            detected="true",
        )

    def test_event_validation_failure_fails_closed(self):
        output = self.normalize(EVENT_VALIDATION_OUTCOME="failure")
        self.assert_normalized(
            output,
            has_breaking="false",
            acknowledged="false",
            result="failure",
            detected="false",
        )

    def test_checkout_failure_fails_closed(self):
        output = self.normalize(CHECKOUT_OUTCOME="failure")
        self.assert_normalized(
            output,
            has_breaking="false",
            acknowledged="false",
            result="failure",
            detected="false",
        )

    def test_guard_action_failure_fails_closed(self):
        output = self.normalize(GUARD_OUTCOME="failure")
        self.assert_normalized(
            output,
            has_breaking="false",
            acknowledged="false",
            result="failure",
            detected="false",
        )

    def test_missing_breaking_boolean_fails_closed(self):
        output = self.normalize(RAW_HAS_BREAKING_CHANGES="")
        self.assert_normalized(
            output,
            has_breaking="false",
            acknowledged="false",
            result="failure",
            detected="false",
        )

    def test_malformed_breaking_boolean_fails_closed(self):
        output = self.normalize(RAW_HAS_BREAKING_CHANGES="yes")
        self.assert_normalized(
            output,
            has_breaking="false",
            acknowledged="false",
            result="failure",
            detected="false",
        )

    def test_missing_acknowledgement_boolean_fails_closed(self):
        output = self.normalize(RAW_APPROVED="")
        self.assert_normalized(
            output,
            has_breaking="false",
            acknowledged="false",
            result="failure",
            detected="false",
        )

    def test_malformed_acknowledgement_boolean_fails_closed(self):
        output = self.normalize(RAW_APPROVED="approved")
        self.assert_normalized(
            output,
            has_breaking="false",
            acknowledged="false",
            result="failure",
            detected="false",
        )


class EnforcementTests(unittest.TestCase):
    def enforce(self, **overrides):
        env = {
            "DRY_RUN": "false",
            "GUARD_JOB_RESULT": "success",
            "GUARD_RESULT": "success",
            "HAS_BREAKING_CHANGES": "false",
            "BREAKING_CHANGE_ACKNOWLEDGED": "false",
            "DETECTION_SUCCEEDED": "true",
        }
        env.update(overrides)
        return execute_body(ENFORCE_BODY, env)[0]

    def test_live_successful_guard_passes(self):
        result = self.enforce()
        self.assertEqual(0, result.returncode, result.stderr)

    def test_live_failure_output_blocks(self):
        result = self.enforce(GUARD_RESULT="failure")
        self.assertNotEqual(0, result.returncode)

    def test_live_missing_output_blocks(self):
        result = self.enforce(GUARD_RESULT="")
        self.assertNotEqual(0, result.returncode)

    def test_live_failed_guard_job_blocks_even_with_success_output(self):
        result = self.enforce(GUARD_JOB_RESULT="failure")
        self.assertNotEqual(0, result.returncode)

    def test_live_cancelled_guard_job_blocks_even_with_success_output(self):
        result = self.enforce(GUARD_JOB_RESULT="cancelled")
        self.assertNotEqual(0, result.returncode)

    def test_live_skipped_guard_job_blocks_even_with_success_output(self):
        result = self.enforce(GUARD_JOB_RESULT="skipped")
        self.assertNotEqual(0, result.returncode)

    def test_live_failed_detection_blocks_even_with_success_output(self):
        result = self.enforce(DETECTION_SUCCEEDED="false")
        self.assertNotEqual(0, result.returncode)

    def test_live_missing_detection_flag_blocks_even_with_success_output(self):
        result = self.enforce(DETECTION_SUCCEEDED="")
        self.assertNotEqual(0, result.returncode)

    def test_dry_run_failed_guard_job_is_non_blocking(self):
        result = self.enforce(
            DRY_RUN="true", GUARD_JOB_RESULT="failure", GUARD_RESULT="failure"
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn(
            "Breaking change guard dry run: job=failure result=failure", result.stdout
        )
        self.assertIn("acknowledged=false", result.stdout)

    def test_dry_run_cancelled_guard_job_is_non_blocking(self):
        result = self.enforce(
            DRY_RUN="true", GUARD_JOB_RESULT="cancelled", GUARD_RESULT=""
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn(
            "Breaking change guard dry run: job=cancelled result=missing", result.stdout
        )
        self.assertIn("acknowledged=false", result.stdout)

    def test_dry_run_skipped_guard_job_is_non_blocking(self):
        result = self.enforce(
            DRY_RUN="true", GUARD_JOB_RESULT="skipped", GUARD_RESULT=""
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn(
            "Breaking change guard dry run: job=skipped result=missing", result.stdout
        )
        self.assertIn("acknowledged=false", result.stdout)

    def test_dry_run_failed_detection_is_non_blocking(self):
        result = self.enforce(DRY_RUN="true", DETECTION_SUCCEEDED="false")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("detection_succeeded=false", result.stdout)


class WorkflowStructureTests(unittest.TestCase):
    def test_guard_contract_is_not_configurable_by_workflow_inputs(self):
        inputs = extract_workflow_call_section(WORKFLOW, "inputs")
        keys = mapping_keys(inputs, 6)
        forbidden = {
            "enable_breaking_change_guard",
            "breaking_change_target",
            "breaking_change_acknowledgement",
            "acknowledgement_match_mode",
        }
        self.assertTrue(
            forbidden.isdisjoint(keys), sorted(forbidden.intersection(keys))
        )
        unexpected = [
            key
            for key in keys
            if ("breaking" in key or "acknowledgement" in key)
            and key not in APPROVAL_GATE_INPUTS
        ]
        self.assertFalse(unexpected, unexpected)

    def test_guard_uses_fixed_author_acknowledgement_exact_mode_and_released_action(
        self,
    ):
        job = extract_job(WORKFLOW, "breaking-change-guard")
        step = extract_step(job, "Detect breaking changes")
        self.assertIn(
            "uses: LerianStudio/github-actions-shared-workflows/src/validate/breaking-change-guard@v1",
            step,
        )
        self.assertIn(f"breaking-change-acknowledgement: '{ACKNOWLEDGEMENT}'", step)
        self.assertIn("acknowledgement-match-mode: exact-visible-line", step)
        outputs = extract_workflow_call_section(WORKFLOW, "outputs")
        self.assertIn("exact PR author acknowledgement", outputs)
        self.assertIn("does not grant maintainer permission", outputs)

    def test_detector_and_comment_acknowledgement_literals_are_identical(self):
        # One literal tells the author what to paste, the other decides whether
        # what they pasted counts. A drift between them leaves the gate teaching
        # a line that fails the check it is explaining.
        detector_step = extract_step(
            extract_job(WORKFLOW, "breaking-change-guard"), "Detect breaking changes"
        )
        detector_literal = re.search(
            r"(?m)^\s*breaking-change-acknowledgement: '(?P<value>[^']*)'$",
            detector_step,
        )
        self.assertIsNotNone(detector_literal)
        self.assertEqual(ACKNOWLEDGEMENT, detector_literal.group("value"))

        # The gate is handed the same literal explicitly — relying on its
        # default to coincide is what made these drift-prone in the first place.
        gate_job = extract_job(WORKFLOW, "breaking-change-approval")
        gate_literal = re.search(
            r"(?m)^\s*author_acknowledgement: '(?P<value>[^']*)'$", gate_job
        )
        self.assertIsNotNone(
            gate_literal, "pr-validation must pass the acknowledgement explicitly"
        )
        self.assertEqual(
            detector_literal.group("value"), gate_literal.group("value")
        )

    def test_guard_checkout_has_full_history_without_persisted_credentials(self):
        job = extract_job(WORKFLOW, "breaking-change-guard")
        step = extract_step(job, "Checkout code")
        self.assertIn("fetch-depth: 0", step)
        self.assertIn("persist-credentials: false", step)

    def test_guard_detector_has_contents_read_only(self):
        job = extract_job(WORKFLOW, "breaking-change-guard")
        permissions = re.search(
            r"(?m)^    permissions:\n(?P<body>(?:      .*\n)+)", job
        )
        self.assertIsNotNone(permissions)
        self.assertEqual("contents: read", permissions.group("body").strip())

    def test_draft_pull_requests_still_reach_guard_enforcement(self):
        guard_job = extract_job(WORKFLOW, "breaking-change-guard")
        blocking_job = extract_job(WORKFLOW, "blocking-checks")
        enforcement = extract_step(blocking_job, "Enforce breaking change guard")
        collection = extract_step(blocking_job, "Collect results and enforce blocking")
        self.assertNotIn("draft", guard_job)
        self.assertRegex(blocking_job, r"(?m)^    if: always\(\)$")
        self.assertRegex(enforcement, r"(?m)^        if: always\(\)$")
        self.assertIn("github.event.pull_request.draft != true", collection)

    def test_reporter_and_summary_receive_guard_and_blocking_runtime_results(self):
        for job_id, step_name in (
            ("pr-checks-summary", "PR Checks Summary"),
            ("pr-validation-report", "Post PR validation summary comment"),
        ):
            with self.subTest(step=step_name):
                job = extract_job(WORKFLOW, job_id)
                step = extract_step(job, step_name)
                self.assertIn("breaking-change-result:", step)
                self.assertIn("needs.breaking-change-guard.result == 'success'", step)
                self.assertIn(
                    "needs.breaking-change-guard.outputs.result == 'success'", step
                )
                self.assertIn("blocking-checks-result:", step)
                self.assertIn("needs.blocking-checks.result == 'success'", step)

    def test_slack_status_includes_guard_output_and_blocking_job_states(self):
        job = extract_job(WORKFLOW, "notify")
        required = (
            "needs.breaking-change-guard.result != 'success'",
            "needs.breaking-change-guard.outputs.result != 'success'",
            "needs.blocking-checks.result != 'success'",
        )
        for expression in required:
            with self.subTest(expression=expression):
                self.assertGreaterEqual(job.count(expression), 2)

    def test_public_outputs_fail_closed(self):
        outputs = extract_workflow_call_section(WORKFLOW, "outputs")
        self.assertIn(
            "value: ${{ jobs.breaking-change-guard.outputs.has-breaking-changes == 'true' && 'true' || 'false' }}",
            outputs,
        )
        self.assertIn(
            "value: ${{ jobs.breaking-change-guard.outputs.approved == 'true' && 'true' || 'false' }}",
            outputs,
        )
        self.assertIn(
            "value: ${{ jobs.breaking-change-guard.outputs.result == 'success' && 'success' || 'failure' }}",
            outputs,
        )

    def test_go_and_js_workflows_forward_fail_closed_outputs_without_guard_inputs(self):
        for name, text in (("go", GO_WORKFLOW), ("js", JS_WORKFLOW)):
            with self.subTest(workflow=name):
                outputs = extract_workflow_call_section(text, "outputs")
                inputs = extract_workflow_call_section(text, "inputs")
                self.assertIn(
                    "jobs.metadata.outputs.has_breaking_changes || 'false'", outputs
                )
                self.assertIn(
                    "jobs.metadata.outputs.breaking_change_approved || 'false'", outputs
                )
                self.assertIn(
                    "jobs.metadata.outputs.breaking_change_result || 'failure'", outputs
                )
                input_keys = mapping_keys(inputs, 6)
                unexpected = [
                    key
                    for key in input_keys
                    if ("breaking" in key or "acknowledgement" in key)
                    and key not in APPROVAL_GATE_INPUTS
                ]
                self.assertFalse(unexpected, unexpected)

    def test_analysis_workflows_expose_scoped_test_runner_overrides(self):
        cases = (
            (
                "go-integration",
                GO_WORKFLOW,
                GO_ANALYSIS,
                "integration_test_runner_type",
                "go-analysis",
                "integration-tests",
            ),
            (
                "frontend-tests",
                JS_WORKFLOW,
                FRONTEND_ANALYSIS,
                "test_runner_type",
                "frontend-analysis",
                "tests",
            ),
        )
        for (
            name,
            umbrella,
            analysis,
            input_name,
            umbrella_job,
            analysis_job,
        ) in cases:
            with self.subTest(workflow=name):
                for text in (umbrella, analysis):
                    inputs = extract_workflow_call_section(text, "inputs")
                    entry = extract_mapping_entry(inputs, input_name, 6)
                    self.assertRegex(entry, r"(?m)^        type: string$")
                    self.assertRegex(entry, r"(?m)^        default: ''$")

                self.assertIn(
                    f"{input_name}: ${{{{ inputs.{input_name} }}}}",
                    extract_job(umbrella, umbrella_job),
                )
                self.assertIn(
                    f"runs-on: ${{{{ inputs.{input_name} || vars.GENERAL_RUNNERS || inputs.runner_type }}}}",
                    extract_job(analysis, analysis_job),
                )


class CommentPermissionTests(unittest.TestCase):
    def test_jobs_that_comment_on_a_pull_request_can_write_to_it(self):
        # Commenting on a pull request needs `pull-requests: write`. The
        # issue-comments endpoint is the one used, but GitHub authorises the
        # subject as a pull request, so `issues: write` is not enough — it
        # covers real issues only. The mistake fails as a 403 at runtime, and
        # these steps are continue-on-error, so it reports success.
        workflow = yaml.safe_load(WORKFLOW)
        top_level = workflow.get("permissions") or {}

        for job_id, job in workflow["jobs"].items():
            if not isinstance(job, dict):
                continue
            body = yaml.safe_dump(job)
            if not any(
                marker in body
                for marker in ("createComment", "updateComment", "issues/comments")
            ):
                continue

            with self.subTest(job=job_id):
                # A job-level block replaces the workflow's, it does not merge,
                # so an explicit block has to carry the permission itself.
                effective = job.get("permissions") or top_level
                self.assertEqual(
                    "write",
                    effective.get("pull-requests"),
                    f"{job_id} comments on a pull request and would take a 403",
                )

class AdvisoryChecksTests(unittest.TestCase):
    def test_advisory_checks_do_not_cascade_off_a_blocking_failure(self):
        job = extract_job(WORKFLOW, "advisory-checks")
        condition = next(
            line for line in job.splitlines() if line.strip().startswith("if:")
        )
        # Advisory by definition: a wrong title or a missing signature must not
        # also cost the pull request its size label, its auto-labels and its
        # assignee. Those are most useful precisely on a pull request that is
        # already in trouble.
        self.assertNotIn("needs.blocking-checks.result", condition)
        self.assertIn("always()", condition)
        self.assertIn("github.event.pull_request.draft != true", condition)

    def test_advisory_checks_cannot_become_a_new_blocker(self):
        job = extract_job(WORKFLOW, "advisory-checks")
        # Running them unconditionally is only safe while none of them can fail
        # the job — otherwise this change would turn three advisory checks into
        # a blocking one.
        for step_name in ("Check PR metadata", "Check PR size", "Auto-label PR"):
            with self.subTest(step=step_name):
                self.assertIn("continue-on-error: true", extract_step(job, step_name))

    def test_the_reports_survive_an_advisory_failure(self):
        # The checkout in advisory-checks has no continue-on-error, so the job
        # can still fail. Everything that reports must run anyway.
        #
        # Read from the parsed job, not from its text: `assertIn` over the whole
        # job body is satisfied by a step, or even by this comment, while the
        # job-level `needs` and `if` say something else entirely.
        jobs = yaml.safe_load(WORKFLOW)["jobs"]
        for job_id in ("pr-checks-summary", "pr-validation-report"):
            with self.subTest(job=job_id):
                self.assertIn("advisory-checks", jobs[job_id]["needs"])
                self.assertIn("always()", jobs[job_id]["if"])


class ApprovalGateStructureTests(unittest.TestCase):
    """The human approval gate — wiring that must not drift.

    Every assertion here corresponds to a way the gate could keep reporting green
    while gating nothing, which is the only failure mode that matters for a
    control like this.
    """

    def test_reusable_workflow_offers_no_manual_trigger(self):
        self.assertIn("workflow_call:", APPROVAL_WORKFLOW)
        self.assertNotIn("workflow_dispatch:", APPROVAL_WORKFLOW)

    def test_environment_is_a_literal_not_an_expression(self):
        job = extract_job(APPROVAL_WORKFLOW, "approval")
        self.assertIn("environment: breaking-approval", job)
        # An `environment:` built from an input could be pointed at an ungated
        # Environment by a caller. Same reasoning as tier-promotion.yml.
        self.assertNotIn("environment: ${{", APPROVAL_WORKFLOW)

    def test_approval_job_only_runs_when_there_is_something_to_approve(self):
        job = extract_job(APPROVAL_WORKFLOW, "approval")
        self.assertIn(
            "needs.detect.outputs.has-breaking-changes == 'true'",
            job,
        )
        self.assertIn("!inputs.dry_run", job)
        # The preflight lives in `request`; approving must not be reachable when
        # it failed, or an unprotected Environment would wave the change through.
        self.assertIn("needs.request.result == 'success'", job)

    def test_every_orchestrated_composite_exists_with_its_readme(self):
        for path in APPROVAL_COMPOSITES:
            with self.subTest(composite=path):
                directory = REPO_ROOT / path
                self.assertTrue((directory / "action.yml").is_file(), path)
                self.assertTrue((directory / "README.md").is_file(), path)
                # Ref deliberately not asserted while the composites are still
                # unreleased: `@v1` cannot resolve a composite this very pull
                # request introduces. test_composite_refs_are_pinned below is
                # what keeps the ref honest.
                self.assertIn(
                    f"LerianStudio/github-actions-shared-workflows/{path}@",
                    APPROVAL_WORKFLOW,
                )

    def test_composite_refs_are_pinned_to_a_channel_not_a_feature_branch(self):
        refs = set(
            re.findall(
                r"LerianStudio/github-actions-shared-workflows/src/[^@\s]+@(\S+)",
                APPROVAL_WORKFLOW,
            )
        )
        allowed = {"v1", "develop"}
        stray = sorted(refs - allowed)
        self.assertFalse(
            stray,
            f"composites must resolve through {sorted(allowed)}, not a feature "
            f"branch that disappears when it is deleted: {stray}",
        )

    def test_preflight_runs_before_the_gate_and_fails_closed(self):
        step = extract_step(
            extract_job(APPROVAL_WORKFLOW, "request"),
            "Verify the breaking-approval Environment is protected",
        )
        self.assertIn("src/validate/environment-protection@", step)
        self.assertIn("environment: breaking-approval", step)
        # Where the reviewers come from is asserted in the CODEOWNERS test.
        # The composite is what must refuse. Every branch that cannot prove the
        # Environment gates something has to exit non-zero, never warn.
        self.assertIn("required_reviewers", ENVIRONMENT_PROTECTION)
        self.assertGreaterEqual(ENVIRONMENT_PROTECTION.count("exit 1"), 7)

    def test_environment_is_never_created_without_reviewers(self):
        # Creating it without reviewers would produce the exact failure the
        # preflight exists to prevent: a gate that approves itself.
        self.assertIn('if [ -z "$REVIEWERS" ]; then', ENVIRONMENT_PROTECTION)
        self.assertIn("cannot be created as a gate", ENVIRONMENT_PROTECTION)

    def test_an_existing_environment_is_never_rewritten(self):
        # A PUT replaces the whole configuration, so repairing an existing
        # Environment would silently drop a wait timer or branch policy.
        self.assertIn("Not changing it from here", ENVIRONMENT_PROTECTION)
        # The only PUT must sit on the creation path, after the 404 branch.
        created_at = ENVIRONMENT_PROTECTION.index("created=true")
        put_at = ENVIRONMENT_PROTECTION.index("--method PUT")
        self.assertLess(put_at, created_at)
        self.assertEqual(1, ENVIRONMENT_PROTECTION.count("--method PUT"))

    def test_reviewers_come_from_codeowners_on_the_base_ref(self):
        step = extract_step(
            extract_job(APPROVAL_WORKFLOW, "request"),
            "Derive the reviewers from CODEOWNERS",
        )
        self.assertIn("src/validate/codeowners-reviewers@", step)
        # The base ref, never the head: a CODEOWNERS from the pull request
        # branch would let the author choose who approves their own change.
        self.assertIn("ref: ${{ needs.detect.outputs.base-ref }}", step)
        self.assertNotIn("head", step)
        # Explicit reviewers win, then CODEOWNERS, then the fallback. Order
        # matters: a caller that named its reviewers must not be overridden by
        # a repository-wide default, and the default must not be reached while
        # CODEOWNERS still has an answer.
        workflow = yaml.safe_load(APPROVAL_WORKFLOW)
        preflight = next(
            s
            for s in workflow["jobs"]["request"]["steps"]
            if s.get("name") == "Verify the breaking-approval Environment is protected"
        )
        expression = " ".join(preflight["with"]["reviewers"].split())
        self.assertEqual(
            "${{ inputs.approval_reviewers != '' && inputs.approval_reviewers"
            " || (steps.codeowners.outputs.reviewers != ''"
            " && steps.codeowners.outputs.reviewers"
            " || inputs.fallback_reviewers) }}",
            expression,
        )

    def test_a_repository_without_a_catch_all_rule_still_has_a_reviewer(self):
        # Measured across the consumers before adding this: four of five
        # CODEOWNERS files carry no `*` rule, and `codeowners-reviewers` reads
        # the catch-all by design — a repository-wide gate should ask the
        # repository-wide owner. So those four resolved nobody, the Environment
        # could not be created, and the first breaking change in each would
        # have been blocked by a gate with no one able to answer it.
        gate = yaml.safe_load(APPROVAL_WORKFLOW)
        self.assertIn("fallback_reviewers", gate[True]["workflow_call"]["inputs"])
        # Empty by default: refusing is still better than inventing a reviewer.
        self.assertEqual(
            "", gate[True]["workflow_call"]["inputs"]["fallback_reviewers"]["default"]
        )

        # The umbrellas expose it, and `pr-validation` sources the default from
        # an organisation variable rather than naming a team in the code.
        validation = yaml.safe_load(
            (REPO_ROOT / ".github" / "workflows" / "pr-validation.yml").read_text(
                encoding="utf-8"
            )
        )
        forwarded = validation["jobs"]["breaking-change-approval"]["with"][
            "fallback_reviewers"
        ]
        self.assertIn("vars.BREAKING_APPROVAL_FALLBACK_REVIEWERS", forwarded)
        self.assertIn("inputs.breaking_change_fallback_reviewers", forwarded)

        for name in ("go-pr-validation", "js-pr-validation"):
            umbrella = yaml.safe_load(
                (REPO_ROOT / ".github" / "workflows" / f"{name}.yml").read_text(
                    encoding="utf-8"
                )
            )
            self.assertIn(
                "breaking_change_fallback_reviewers",
                umbrella[True]["workflow_call"]["inputs"],
                name,
            )

        # No team name in the code — the organisation variable is the source.
        self.assertNotIn("G_Github_Devops", APPROVAL_WORKFLOW)

    def test_the_waiting_comment_links_instead_of_mentioning(self):
        rendered = render_reporter("waiting")
        # Links to the commit, the decision, the reviewers and the docs.
        for fragment in (
            "](https://github.com/LerianStudio/example/commit/abc1234567)",
            "[![Review the pending deployment](https://img.shields.io/badge/",
            "](https://github.com/orgs/LerianStudio/teams/devops)",
            "[How this gate works](https://example.invalid/docs)",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, rendered)

        # The pending deployment already notifies the reviewers; a bare @mention
        # would ping the whole team again for the same thing.
        #
        # Same technique as the decider test: delete the complete links, then
        # require nothing to remain. This assertion used to check only that an
        # `@` was preceded by `[`, which a bare `[@LerianStudio/devops]` with no
        # target satisfies.
        without_links = re.sub(
            r"\[@LerianStudio/\w+\]\(https://github\.com/orgs/LerianStudio/teams/\w+\)",
            "",
            rendered,
        )
        self.assertNotIn("@LerianStudio/", without_links)

    def test_only_one_approval_request_stays_open_per_pull_request(self):
        job = extract_job(APPROVAL_WORKFLOW, "approval")
        # Every push queues another pending deployment, and the old ones do not
        # expire on their own: approving a superseded one approves a revision
        # nobody is merging. Cancelling is also what expires an approval, so the
        # next revision cannot inherit a yes given to different code.
        self.assertIn("concurrency:", job)
        self.assertIn(
            "group: breaking-approval-${{ github.repository }}"
            "-${{ needs.detect.outputs.pr-number }}",
            job,
        )
        self.assertIn("cancel-in-progress: true", job)

    def test_a_superseded_run_leaves_the_pull_request_alone(self):
        body = extract_run_body(
            extract_job(APPROVAL_WORKFLOW, "outcome"), "Resolve the verdict"
        )
        # The cancelled run still reaches the verdict. Without this it would
        # overwrite the live revision's comment with "did not complete".
        self.assertIn("state=superseded", body)
        self.assertIn('"$live_sha" != "$HEAD_SHA"', body)
        # A changed head is not the only way to be superseded: `edited` queues a
        # new run on the very same commit, so a cancelled approval has to count
        # on its own. Observed on #906 — editing the description replaced the
        # run, and the comparison above saw nothing wrong while the comment was
        # overwritten with "decision not recorded".
        # A cancellation is a reason to look, not a verdict. It passes only
        # with supersession established — a newer run, or the head having moved
        # on. Treating every cancellation as supersession reported success for
        # revisions nobody approved, which is what Radagast caught on #926.
        self.assertIn('[ "$APPROVAL_RESULT" = "cancelled" ]', body)
        self.assertIn("actions/workflows/${workflow_id}/runs?branch=${HEAD_REF}", body)
        # Scoped to this workflow, never to the branch at large: the sibling
        # runs from the same push start later and carry higher ids, so the
        # broad query answers "superseded" for every cancellation.
        self.assertNotIn("/actions/runs?branch=", body)
        _, stranded = run_verdict(APPROVAL_RESULT="cancelled", MOCK_NEWER_RUNS="0")
        self.assertEqual("unresolved", stranded["state"])

    def test_a_cancelled_approval_stops_before_anything_can_act_on_it(self):
        # Run it, with a recorded rejection sitting right there. The branch has
        # to stop: if it falls through, the rejection downstream wins, the
        # verdict comes back `rejected`, and the pull request gets closed —
        # because a concurrency cancellation raced a reviewer.
        # With a newer run established, so the branch under test is the
        # cancellation one. The guarantee is that it stops before the rejection
        # downstream can close the pull request.
        _, outputs = run_verdict(
            APPROVAL_RESULT="cancelled", REJECTERS="dave", MOCK_NEWER_RUNS="1"
        )
        self.assertEqual("superseded", outputs["state"])
        self.assertNotEqual("rejected", outputs["state"])

    def test_a_standing_approval_skips_the_request_entirely(self):
        step = extract_step(
            extract_job(APPROVAL_WORKFLOW, "request"),
            "Request the approval on the pull request",
        )
        # Observed on #920: with the approval already standing, the run still
        # announced "needs a decision" and added the pending label, and the
        # verdict took both back seconds later. A flicker in the timeline for a
        # decision that was never in question.
        self.assertIn("steps.reuse.outputs.already-approved != 'true'", step)

    def test_the_decider_is_linked_not_mentioned(self):
        for state, env, who in (
            ("approved", {"APPROVERS": "carol"}, "carol"),
            ("rejected", {"REJECTERS": "dave"}, "dave"),
        ):
            with self.subTest(state=state):
                rendered = render_reporter(state, **env)
                self.assertIn(f"[@{who}](https://github.com/{who})", rendered)

                # Linked, not mentioned: the person named is the one who just
                # acted, so a notification tells them what they already know.
                #
                # Checked by deleting the complete links and requiring nothing
                # to remain. "preceded by `[`" would accept a bare `[@carol]`
                # with no target — present, bracketed, and not a link.
                without_links = re.sub(
                    rf"\[@{who}\]\(https://github\.com/{who}\)", "", rendered
                )
                self.assertNotIn(f"@{who}", without_links)

    def test_an_approval_already_given_is_not_asked_for_again(self):
        # The reviewer said yes to a breaking change. A push that leaves that
        # change alone must not put the same question back in their queue —
        # asking repeatedly for unchanged content is how a gate stops being
        # read. The approval job is skipped, so there is no Environment
        # decision; the verdict comes from the record on the pull request.
        _, outputs = run_verdict(ALREADY_APPROVED="true", APPROVAL_RESULT="skipped")
        self.assertEqual("approved", outputs["state"])
        self.assertEqual("success", outputs["result"])

        job = extract_job(APPROVAL_WORKFLOW, "approval")
        self.assertIn(
            "needs.request.outputs.already-approved != 'true'",
            job,
            "the Environment gate must be skipped when the change was already approved",
        )

    def test_environment_work_stays_inside_its_scope(self):
        workflow = yaml.safe_load(APPROVAL_WORKFLOW)
        # Out of scope no approval is required, so nothing that touches the
        # Environment may run there. #918 removed the only thing enforcing this
        # when it started preserving the caller's real detection.
        self.assertIn(
            "needs.detect.outputs.in-scope == 'true'",
            str(workflow["jobs"]["approval"]["if"]),
        )
        gated = {
            "Check for a prior approval of the same change",
            "Derive the reviewers from CODEOWNERS",
            "Verify the breaking-approval Environment is protected",
            "Request the approval on the pull request",
        }
        for step in workflow["jobs"]["request"]["steps"]:
            name = step.get("name")
            if name in gated:
                with self.subTest(step=name):
                    self.assertIn("in-scope == 'true'", str(step.get("if", "")))
            elif name == "Report the acknowledgement requirement":
                # The one that must run outside scope: the acknowledgement is
                # enforced everywhere, so the author still needs the line.
                self.assertIn("in-scope != 'true'", str(step.get("if", "")))

    def test_a_cancellation_passes_only_when_superseded(self):
        body = extract_run_body(
            extract_job(APPROVAL_WORKFLOW, "outcome"), "Resolve the verdict"
        )
        # Run it: cancelled with nothing replacing it must not pass.
        _, outputs = run_verdict(APPROVAL_RESULT="cancelled", MOCK_NEWER_RUNS="0")
        self.assertEqual("unresolved", outputs["state"])
        self.assertNotEqual("superseded", outputs["state"])

        # And the two ways supersession is genuinely established.
        _, by_run = run_verdict(APPROVAL_RESULT="cancelled", MOCK_NEWER_RUNS="2")
        self.assertEqual("superseded", by_run["state"])
        _, by_head = run_verdict(APPROVAL_RESULT="cancelled", LIVE_SHA="def456")
        self.assertEqual("superseded", by_head["state"])

        self.assertIn("actions/workflows/${workflow_id}/runs?branch=${HEAD_REF}", body)

    def test_the_public_breaking_output_reports_detection_out_of_scope(self):
        # A deliberate behaviour change, documented rather than versioned. The
        # reason is specific to this output and not the one that covers the
        # `label` input: the umbrellas do not surface it. Their
        # `has_breaking_changes` comes from the `breaking-change-guard` job,
        # which is unchanged, so only a standalone caller reads this value.
        #
        # It used to be forced to `false` out of scope; it now reports what the
        # caller detected, because a pull request this workflow does not gate
        # can still carry a break and the caller asking deserves the answer.
        out_of_scope = run_detect_normalization(
            IN_SCOPE="false", SUPPLIED_HAS_BREAKING_CHANGES="true"
        )
        self.assertEqual("true", out_of_scope["has-breaking-changes"])
        self.assertEqual("true", out_of_scope["detection-succeeded"])

        # Nothing supplied is still `false` — there is no answer to report, and
        # the gate never scans out of scope.
        nothing_supplied = run_detect_normalization(IN_SCOPE="false")
        self.assertEqual("false", nothing_supplied["has-breaking-changes"])

        # And the description must not promise the old value back. Documenting
        # `false` while emitting `true` is the defect Radagast caught on #926.
        workflow = yaml.safe_load(APPROVAL_WORKFLOW)
        described = workflow[True]["workflow_call"]["outputs"]["has_breaking_changes"][
            "description"
        ]
        self.assertNotIn("Always false when out of scope", described)
        self.assertIn("Behaviour change", described)

    def test_a_failed_enumeration_is_unknown_not_a_clean_bill(self):
        # The step that turns the commit list into a verdict was only ever run
        # out of scope. Radagast proved the gap by mutation: flipping the
        # failed-enumeration branch to report success left the suite green,
        # and that mutation turns "we could not look" into "nothing found" —
        # the one reading the gate exists to refuse.
        #
        # Reached when the pull request is above the 250-commit cap, when the
        # API is unreadable, or when the composite refuses for any other
        # reason. In every one of them nobody has seen the whole change.
        for description, overrides in (
            ("the composite failed", {"COMMITS_OUTCOME": "failure", "BREAKING_COUNT": ""}),
            ("it succeeded but emitted no count", {"BREAKING_COUNT": ""}),
            ("it failed with a stale count", {"COMMITS_OUTCOME": "failure"}),
        ):
            with self.subTest(description):
                outputs = run_detect_normalization(**overrides)
                self.assertEqual("false", outputs["detection-succeeded"], description)
                self.assertEqual("false", outputs["has-breaking-changes"], description)

        # And the verdict downstream has to block on it rather than pass.
        _, verdict = run_verdict(DETECTION_SUCCEEDED="false")
        self.assertEqual("blocked", verdict["state"])
        self.assertEqual("failure", verdict["result"])
        self.assertEqual("false", verdict["approved"])

        # A caller that did its own detection is not blocked by the local
        # enumeration failing — it supplied the answer. The fingerprint is
        # empty, so no approval is reused, and a fresh decision is asked for.
        supplied = run_detect_normalization(
            COMMITS_OUTCOME="failure",
            BREAKING_COUNT="",
            SUPPLIED_HAS_BREAKING_CHANGES="true",
        )
        self.assertEqual("true", supplied["detection-succeeded"])
        self.assertEqual("true", supplied["has-breaking-changes"])

    def test_a_newer_run_of_another_pull_request_is_not_supersession(self):
        # One head branch can carry two pull requests — same branch, different
        # bases. Scoping the query to this workflow leaves that open: the other
        # pull request's run is newer, on this branch, of this workflow, and
        # without the `.pull_requests` filter it would carry a decision for a
        # pull request it knows nothing about.
        runs = {
            "workflow_runs": [
                {"id": 101, "event": "pull_request", "pull_requests": [{"number": 77}]},
                {"id": 102, "event": "pull_request", "pull_requests": [{"number": 77}]},
            ]
        }
        _, other_pr = run_verdict(
            APPROVAL_RESULT="cancelled", MOCK_RUNS_JSON=json.dumps(runs)
        )
        self.assertEqual("unresolved", other_pr["state"])

        # Mixed: the same two, plus one that is actually ours.
        runs["workflow_runs"].append(
            {"id": 103, "event": "pull_request", "pull_requests": [{"number": 42}]}
        )
        _, ours = run_verdict(
            APPROVAL_RESULT="cancelled", MOCK_RUNS_JSON=json.dumps(runs)
        )
        self.assertEqual("superseded", ours["state"])

    def test_a_run_from_a_fork_is_matched_on_the_head_not_the_branch(self):
        # Runs from forks come back with `pull_requests: []`. Dropping them
        # would make every cancellation on a fork unresolved; accepting any run
        # that has none is how a dispatched run passed for a pull request it
        # had nothing to do with. They are matched on the head instead, which
        # ties the run to this revision.
        same_head = {
            "workflow_runs": [
                {
                    "id": 101,
                    "event": "pull_request",
                    "head_sha": "abc123",
                    "pull_requests": [],
                }
            ]
        }
        _, fork = run_verdict(
            APPROVAL_RESULT="cancelled", MOCK_RUNS_JSON=json.dumps(same_head)
        )
        self.assertEqual("superseded", fork["state"])

        other_head = json.loads(json.dumps(same_head))
        other_head["workflow_runs"][0]["head_sha"] = "def456"
        _, unrelated = run_verdict(
            APPROVAL_RESULT="cancelled", MOCK_RUNS_JSON=json.dumps(other_head)
        )
        self.assertEqual("unresolved", unrelated["state"])

    def test_a_dispatched_run_is_not_supersession(self):
        # Reported by @fredcamaral and reproduced: with no event filter, any
        # newer run of this workflow on the branch counted. Dispatch one by
        # hand, cancel the pending approval, and the verdict reads
        # `superseded` — which exits 0. A green gate with no approval, for
        # anybody with write access.
        #
        # `self-pr-validation.yml` enables `workflow_dispatch` and skips
        # validation on it, so the dispatched run does not even have to do
        # anything.
        for description, run in (
            (
                "dispatched, no pull request attached",
                {"id": 101, "event": "workflow_dispatch", "head_sha": "abc123",
                 "pull_requests": []},
            ),
            (
                "dispatched, naming this pull request",
                {"id": 101, "event": "workflow_dispatch", "head_sha": "abc123",
                 "pull_requests": [{"number": 42}]},
            ),
            (
                "a scheduled run on the same branch",
                {"id": 101, "event": "schedule", "head_sha": "abc123",
                 "pull_requests": []},
            ),
        ):
            with self.subTest(description):
                _, outputs = run_verdict(
                    APPROVAL_RESULT="cancelled",
                    MOCK_RUNS_JSON=json.dumps({"workflow_runs": [run]}),
                )
                self.assertEqual("unresolved", outputs["state"], description)

        # And `unresolved` must not pass, which is the half that makes the
        # filter matter.
        body = extract_run_body(
            extract_job(APPROVAL_WORKFLOW, "outcome"), "Record the verdict"
        )
        self.assertIn('[ "$STATE" = "superseded" ]', body)
        self.assertNotIn('[ "$STATE" = "unresolved" ]', body)

    def test_a_reused_approval_must_belong_to_this_pull_request(self):
        step = extract_step(
            extract_job(APPROVAL_WORKFLOW, "request"),
            "Check for a prior approval of the same change",
        )
        # Confirming the named run carried *an* approval proves nothing: every
        # approved breaking change in the repository has such a run, and a
        # record naming one is a sentence anybody with write access can type.
        # The run has to be this pull request's.
        self.assertIn("HEAD_REF:", step)
        self.assertIn('"$run_branch" != "$HEAD_REF"', step)
        # Branch, not `pull_requests`: that field comes back empty on real runs.
        self.assertIn(".head_branch", step)

        detect = extract_job(APPROVAL_WORKFLOW, "detect")
        self.assertIn("head-ref: ${{ steps.scope.outputs.head-ref }}", detect)

    def test_a_commit_subject_cannot_smuggle_an_approval_record(self):
        reporter = (
            REPO_ROOT / "src" / "notify" / "breaking-change-approval-reporter"
            / "action.yml"
        ).read_text(encoding="utf-8")
        # Subjects are author-controlled and get rendered into this comment.
        # One carrying a marker would be collected by the record preserver as
        # though the gate had written it — the author approving their own break
        # by choosing a commit message. Two independent guards, because one
        # guard for a privilege escalation is one too few.
        self.assertIn("s/<!--/\\&lt;!--/g", reporter)
        self.assertIn("awk '/^```/ { fenced = !fenced; next } !fenced'", reporter)

        # And the behaviour, not just its shape.
        rendered = render_reporter(
            "waiting",
            MOCK_SUBJECTS="feat(x)!: <!-- breaking-change-approved: dead run=1 -->",
        )
        self.assertNotIn("<!-- breaking-change-approved:", rendered)
        self.assertIn("&lt;!--", rendered)

    def test_a_forged_approval_record_is_not_believed(self):
        step = extract_step(
            extract_job(APPROVAL_WORKFLOW, "request"),
            "Check for a prior approval of the same change",
        )
        # Anyone with read access can comment, and the fingerprint is computable
        # from public data — so the record alone is writable by a stranger.
        # Two independent conditions must hold before an approval is reused.
        self.assertIn('select(.author_association == "OWNER"', step)
        self.assertIn('or .author_association == "MEMBER"', step)
        # And the run it names has to carry a real Environment approval.
        self.assertIn("actions/runs/${approving_run}/approvals", step)
        self.assertIn('select(.state == "approved")', step)
        self.assertIn('index("breaking-approval")', step)

    def test_the_default_reporter_identity_is_accepted(self):
        step = extract_step(
            extract_job(APPROVAL_WORKFLOW, "request"),
            "Check for a prior approval of the same change",
        )
        # Without MANAGE_TOKEN the reporter writes as `github-actions[bot]`,
        # for which GitHub can report `author_association: NONE`. Filtering on
        # association alone would drop those comments and quietly disable the
        # whole feature for every caller on the default token.
        self.assertIn('.user.login == "github-actions[bot]"', step)

    def test_the_prior_lookup_honours_the_dry_run_contract(self):
        step = extract_step(
            extract_job(APPROVAL_WORKFLOW, "request"),
            "Check for a prior approval of the same change",
        )
        # The repository's contract: a real run is silent beyond one summary,
        # a dry run prints the resolved values. Both halves matter here —
        # a preview that cannot say whether the approval would be reused is
        # not previewing the decision this gate turns on.
        self.assertIn('DRY_RUN: ${{ inputs.dry_run', step)
        self.assertNotIn("&& !inputs.dry_run", step)

        code = "\n".join(
            line for line in step.splitlines() if not line.strip().startswith("#")
        )
        # Writing outputs is not diagnostics. A `{ ... } >> "$GITHUB_OUTPUT"`
        # group puts the redirect on the closing brace, so the `echo` lines
        # inside carry no marker of their own — scan for the group and exempt
        # its contents rather than matching the word on each line.
        in_output_group = False
        output_lines = set()
        group = []
        for index, line in enumerate(code.splitlines()):
            stripped_line = line.strip()
            if stripped_line == "{":
                in_output_group, group = True, []
            elif in_output_group and stripped_line.startswith("}"):
                if "GITHUB_OUTPUT" in stripped_line:
                    output_lines.update(group)
                in_output_group = False
            elif in_output_group:
                group.append(index)

        # Every diagnostic beyond the single summary sits behind the dry-run
        # branch; count them to keep a future one from slipping out.
        for index, line in enumerate(code.splitlines()):
            if "echo " not in line or "GITHUB_OUTPUT" in line or index in output_lines:
                continue
            stripped = line.strip()
            guarded = (
                stripped.startswith('[ "$DRY_RUN" = "true" ] &&')
                or "::notice::" in stripped
                or "::warning::" in stripped
                or stripped.startswith('echo "  ')
            )
            self.assertTrue(guarded, f"ungated diagnostic on a real run: {stripped}")

    def test_every_record_is_tried_not_just_the_first(self):
        step = extract_step(
            extract_job(APPROVAL_WORKFLOW, "request"),
            "Check for a prior approval of the same change",
        )
        # Runs are deleted on the repository's retention schedule, so the oldest
        # record for a fingerprint goes unverifiable first while a newer one is
        # still good. Stopping at the first would ask for an approval on file.
        self.assertIn("while IFS= read -r record", step)
        self.assertNotIn("head -n1 <<< \"$records\"", step)

    def test_only_a_real_approval_writes_a_record(self):
        job = extract_job(APPROVAL_WORKFLOW, "outcome")
        step = extract_step(job, "Report the outcome on the pull request")
        # A reused approval reports `approved` with the gate job skipped. A
        # record naming that run would assert something no log can confirm, and
        # would outlive the real one.
        self.assertIn(
            "needs.approval.result == 'success' && needs.detect.outputs.fingerprint",
            step,
        )

    def test_the_prior_lookup_consumes_the_whole_comment_stream(self):
        step = extract_step(
            extract_job(APPROVAL_WORKFLOW, "request"),
            "Check for a prior approval of the same change",
        )
        # `grep -q` can exit on the first match while `--paginate` is still
        # writing; under pipefail the broken pipe reads as "no match", and the
        # reviewer is asked for an approval they already gave.
        #
        # Comment lines are stripped first: the step explains this very hazard
        # in prose, and matching that prose would make the assertion pass or
        # fail on the explanation rather than on the code.
        code = "\n".join(
            line for line in step.splitlines() if not line.strip().startswith("#")
        )
        self.assertNotIn("grep -q", code)
        self.assertIn("grep -oE", code)

    def test_a_reused_approval_does_not_skip_the_other_guards(self):
        body = extract_run_body(
            extract_job(APPROVAL_WORKFLOW, "outcome"), "Resolve the verdict"
        )
        already_at = body.index('"$ALREADY_APPROVED" = "true"')
        for guard in (
            '"$APPROVAL_RESULT" = "cancelled"',   # superseded by a newer run
            '"$live_sha" != "$HEAD_SHA"',          # head moved under us
            '"$REQUEST_RESULT" != "success"',      # preflight never proved the gate
        ):
            with self.subTest(guard=guard):
                self.assertLess(
                    body.index(guard),
                    already_at,
                    "a standing approval is not a reason to skip the checks that "
                    "say whether this run may speak at all",
                )

    def run_reuse(self, **overrides):
        """Run the step that decides whether an approval is reused."""
        workflow = yaml.safe_load(APPROVAL_WORKFLOW)
        step = next(
            s
            for s in workflow["jobs"]["request"]["steps"]
            if s.get("name") == "Confirm the approval covers this change"
        )
        env = {
            "CANDIDATE_RUN": "4242",
            "CANDIDATE_HEAD": "aaaa111",
            "APPROVED_BY": "carol",
            "APPROVED_FINGERPRINT": "8b5ad0f390f484b1",
            "RESOLVE_OUTCOME": "success",
            "FINGERPRINT": "8b5ad0f390f484b1",
            "PR_NUMBER": "42",
            "DRY_RUN": "false",
        }
        env.update(overrides)
        _, outputs = execute_body(step["run"], env)
        return outputs["already-approved"]

    def test_a_forged_record_cannot_reuse_someone_elses_approval(self):
        # @fredcamaral's report on #926, reproduced as a test.
        #
        # The fingerprint is derived from public commit SHAs, so it is
        # computable before the commit exists. The attack: a member posts a
        # record carrying fp(A,B) that points at the run which approved only A,
        # then pushes the breaking commit B. Every earlier check passes — the
        # record is from a MEMBER, the run is on this branch, the run really
        # did carry an Environment approval — and none of them asks what it
        # approved. The answer used to be taken from the record itself.
        #
        # It is now resolved from the approving run's own head, which nobody
        # can write.
        self.assertEqual(
            "false",
            self.run_reuse(
                APPROVED_FINGERPRINT="8b5ad0f390f484b1",  # what run 4242 approved: A
                FINGERPRINT="50306b18a137bc7b",           # what is here now: A+B
            ),
            "an approval of a different set was reused",
        )

        # The legitimate case it exists for: a push that did not touch the
        # breaking commits — a typo fix — resolves to the same set.
        self.assertEqual("true", self.run_reuse())

        # Unresolvable is not reusable. A deleted run, an unreadable
        # comparison, a pull request past the commit cap: none of them is
        # evidence that the approval still applies.
        self.assertEqual("false", self.run_reuse(RESOLVE_OUTCOME="failure"))
        self.assertEqual("false", self.run_reuse(APPROVED_FINGERPRINT=""))
        self.assertEqual("false", self.run_reuse(CANDIDATE_RUN=""))

    def test_the_reuse_lookup_can_read_the_comparison_it_depends_on(self):
        # The `at-sha` path reads the comparison API, which is repository
        # contents rather than pull request data. Without `contents: read` the
        # comparison fails, the gate reads that as "cannot confirm what that
        # approval covered", and the reviewer is asked again on every push —
        # silently, since the step is `continue-on-error`.
        workflow = yaml.safe_load(APPROVAL_WORKFLOW)
        self.assertEqual("read", workflow["jobs"]["request"]["permissions"]["contents"])

        # And the composite says so, for anyone calling it directly.
        action = yaml.safe_load(
            (
                REPO_ROOT / "src" / "validate" / "breaking-change-commits"
                / "action.yml"
            ).read_text(encoding="utf-8")
        )
        self.assertIn("contents: read", action["inputs"]["github-token"]["description"])
        self.assertIn("contents: read", action["inputs"]["at-sha"]["description"])

    def test_the_approved_set_is_read_from_the_run_not_the_record(self):
        workflow = yaml.safe_load(APPROVAL_WORKFLOW)
        steps = workflow["jobs"]["request"]["steps"]

        # The lookup hands over a candidate and the run's own head. It must not
        # decide reuse by itself any more.
        lookup = extract_step(
            extract_job(APPROVAL_WORKFLOW, "request"),
            "Check for a prior approval of the same change",
        )
        self.assertIn("candidate-head=", lookup)
        self.assertNotIn("already-approved=", lookup)
        # `.head_sha` comes from the run, beside the branch it is already
        # verified against.
        self.assertIn(".head_sha", lookup)

        # The resolver is pointed at that head, never at the current one.
        resolve = next(
            s for s in steps if s.get("name") == "Resolve what the approving run approved"
        )
        self.assertEqual(
            "${{ steps.prior.outputs.candidate-head }}", resolve["with"]["at-sha"]
        )
        self.assertIn("breaking-change-commits@", resolve["uses"])

        # And the job publishes the confirmed answer, not the candidate.
        self.assertEqual(
            "${{ steps.reuse.outputs.already-approved }}",
            workflow["jobs"]["request"]["outputs"]["already-approved"],
        )

    def test_two_approvers_serialise_into_one_output_value(self):
        # An Environment can require more than one reviewer, and the approvals
        # API answers one login per line. Written straight out, the second
        # lands on its own line with no `=`, the runner rejects it, and this
        # step fails — which takes the whole reuse contract down with it:
        # `request` fails, the verdict reads `blocked`, and a breaking set that
        # was already approved is blocked again on every push.
        #
        # Asserting on the source order of the statements could not see this.
        # Run the serialisation and read it back the way the runner does.
        step = extract_step(
            extract_job(APPROVAL_WORKFLOW, "request"),
            "Check for a prior approval of the same change",
        )
        serialise = next(
            line.strip()
            for line in step.splitlines()
            if line.strip().startswith("approved_by=$(printf")
        )
        emit = 'echo "approved-by=${approved_by}" >> "$GITHUB_OUTPUT"'

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "out"
            output.touch()
            result = subprocess.run(
                ["bash", "-c", f'set -euo pipefail\n{serialise}\n{emit}'],
                env={
                    "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                    "approved_by": "alice\nbob",
                    "GITHUB_OUTPUT": str(output),
                },
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            written = output.read_text(encoding="utf-8").splitlines()

        # Every line the runner reads has to be an assignment. This is the
        # check that fails on the unserialised value.
        for line in written:
            self.assertIn("=", line, f"the runner would reject {line!r}")
        self.assertEqual(["approved-by=alice,bob"], written)

        # Comma-separated because that is what the reporter parses: both
        # names come through linked, not one name and a stray word.
        rendered = render_reporter("approved", APPROVERS="alice,bob")
        self.assertIn("[@alice](", rendered)
        self.assertIn("[@bob](", rendered)

    def test_a_blocked_gate_does_not_assert_what_it_could_not_establish(self):
        # `blocked` means nothing was established. Labelling the pull request
        # `breaking-change` there asserts exactly what the comment beside it
        # calls unknown — and a transient detection failure would brand a pull
        # request that carries no break at all.
        blocked = run_reporter_labels("blocked")
        self.assertNotIn(("add-label", "breaking-change"), list(zip(blocked, blocked[1:])))
        # The pending label still comes off — nothing is waiting on a decision
        # when the gate never got far enough to ask for one.
        self.assertEqual(["remove-label", "awaiting-breaking-approval"], blocked)
        # And the states that did establish the fact still assert it.
        self.assertIn("breaking-change", run_reporter_labels("waiting"))

        # Nor does it blame a stage it cannot know failed: `blocked` is also
        # reached with detection successful and the request stage failing —
        # an Environment preflight refusing an unprotected `breaking-approval`.
        _, from_request = run_verdict(
            REQUEST_RESULT="failure", DETECTION_SUCCEEDED="true"
        )
        self.assertEqual("blocked", from_request["state"])
        rendered = render_reporter("blocked", ACKNOWLEDGED="")
        self.assertIn("did not reach a verdict", rendered)
        self.assertNotIn("Detection did not complete", rendered)

    def test_an_unevaluated_acknowledgement_is_never_reported_as_missing(self):
        # Chained: what normalization emits when detection fails is what the
        # reporter renders. `false` there would tell an author who may well
        # have written the line to add a line no check evaluated.
        for description, overrides in (
            ("local enumeration failed", {"COMMITS_OUTCOME": "failure", "BREAKING_COUNT": ""}),
            ("the caller reported unknown", {"SUPPLIED_HAS_BREAKING_CHANGES": "unknown"}),
            ("the caller sent nonsense", {"SUPPLIED_HAS_BREAKING_CHANGES": "maybe"}),
        ):
            with self.subTest(description):
                normalized = run_detect_normalization(**overrides)
                self.assertEqual("", normalized["acknowledged"], description)
                rendered = render_reporter(
                    "blocked", ACKNOWLEDGED=normalized["acknowledged"]
                )
                self.assertNotIn("Add this exact line", rendered, description)

        # And one that really was evaluated still gets its instructions.
        asked = render_reporter("blocked", ACKNOWLEDGED="false", ACK_LINE="the line")
        self.assertIn("Add this exact line", asked)

    def test_the_waiting_comment_names_the_commits_the_gate_judged(self):
        # The gate already resolved these to build the fingerprint, and its
        # `subjects` output had no consumer while the reporter listed them a
        # second time off its own API call. Two readings of the same pull
        # request that can disagree, for one extra call per run.
        rendered = render_reporter(
            "waiting",
            SUBJECTS="feat(x)!: drops the old flag\nchore(y): ordinary",
            MOCK_SUBJECTS="feat(api)!: something else entirely",
        )
        self.assertIn("drops the old flag", rendered)
        # Supplied wins over what the API would have said.
        self.assertNotIn("something else entirely", rendered)
        # And it is still a filter, not a passthrough.
        self.assertNotIn("chore(y): ordinary", rendered)

        # Empty still reads them, so a standalone caller needs no resolver.
        standalone = render_reporter(
            "waiting", MOCK_SUBJECTS="feat(api)!: read from the API"
        )
        self.assertIn("read from the API", standalone)

        # The defang applies to the supplied set too — it arrives from the
        # same author-written commit messages.
        smuggled = render_reporter(
            "waiting", SUBJECTS="feat(z)!: <!-- breaking-change-approved: dead run=1 -->"
        )
        self.assertNotIn("<!-- breaking-change-approved:", smuggled)

        # And the gate forwards it.
        workflow = yaml.safe_load(APPROVAL_WORKFLOW)
        step = next(
            s
            for s in workflow["jobs"]["request"]["steps"]
            if s.get("with", {}).get("state") == "waiting"
        )
        self.assertEqual(
            "${{ needs.detect.outputs.subjects }}", step["with"]["subjects"]
        )

    def test_the_comment_this_one_replaced_is_retired(self):
        # `breaking-change-comment` owned `<!-- lerian-breaking-change-guard -->`
        # and retired it when the acknowledgement arrived. Removing that job
        # removed its cleanup, so a pull request opened before the changeover
        # keeps an "awaiting acknowledgement" notice forever, beside this
        # comment and contradicting it.
        _, calls = run_reporter_comment(
            "waiting", existing_body="<!-- breaking-change-approval -->\n",
            legacy_ids="3",
        )
        deletes = [call for call in calls if "DELETE" in call]
        self.assertEqual(1, len(deletes), calls)
        self.assertIn("issues/comments/3", deletes[0])

        # Nothing to retire, nothing deleted.
        _, clean = run_reporter_comment(
            "waiting", existing_body="<!-- breaking-change-approval -->\n"
        )
        self.assertFalse([call for call in clean if "DELETE" in call])

        # Narrow on purpose: only a comment the marker opens, and only one
        # written by a bot. Quoting the marker must not get a comment deleted.
        action = (
            REPO_ROOT / "src" / "notify" / "breaking-change-approval-reporter"
            / "action.yml"
        ).read_text(encoding="utf-8")
        self.assertIn('select(.user.type == \\"Bot\\")', action)
        self.assertIn("startswith", action)

    def test_the_records_are_never_rewritten_blind(self):
        # A failed read must not look like "there were none": the rewrite would
        # erase every approval already given on this pull request, and the
        # reviewers would be asked again for changes they had cleared.
        #
        # This was pinned by grepping the composite for its own error message,
        # which proves the words exist and nothing about what runs. A branch
        # that printed them and issued the PATCH anyway would have passed.
        failed, calls = run_reporter_comment("waiting", read_fails=True)
        self.assertEqual(1, failed.returncode)
        self.assertIn("Refusing to rewrite it", failed.stderr)
        self.assertFalse(
            [call for call in calls if "PATCH" in call],
            "the comment was rewritten after the records could not be read",
        )

        # And the successful path actually carries them forward — the half
        # that gives the refusal its point.
        previous = (
            "<!-- breaking-change-approval -->\n\nold body\n\n"
            "<!-- breaking-change-approved: abc123 run=99 -->\n"
        )
        kept, calls = run_reporter_comment("waiting", existing_body=previous)
        self.assertEqual(0, kept.returncode)
        self.assertTrue([call for call in calls if "PATCH" in call])
        self.assertIn("breaking-change-approved: abc123 run=99", kept.posted_body)

        # A marker inside a fenced block is the author's text, not the gate's
        # record — the undo example renders commit subjects in ```diff.
        fenced = (
            "<!-- breaking-change-approval -->\n\n```diff\n"
            "<!-- breaking-change-approved: dead run=1 -->\n```\n"
        )
        smuggled, _ = run_reporter_comment("waiting", existing_body=fenced)
        self.assertNotIn("breaking-change-approved: dead", smuggled.posted_body)

    def test_the_approval_record_survives_the_next_run(self):
        reporter = (
            REPO_ROOT / "src" / "notify" / "breaking-change-approval-reporter"
            / "action.yml"
        ).read_text(encoding="utf-8")
        # Every run rewrites the comment body. Without carrying the records
        # forward, the approval would be forgotten by the very next push, which
        # is the one thing the record exists to prevent.
        self.assertIn("previous_records", reporter)
        self.assertIn("breaking-change-approved: [a-f0-9]+ run=[0-9]+", reporter)
        # Only an approval writes a new record.
        self.assertIn('if [ "$STATE" = "approved" ] && [ -n "$FINGERPRINT" ]', reporter)

    def test_the_gate_checks_out_nothing(self):
        # CodeQL flagged `actions/untrusted-checkout` here, and it was right:
        # a non-privileged workflow was putting a contributor's tree on disk
        # beside MANAGE_TOKEN. Nothing executed it, but nothing needed it —
        # the commits are readable through the API.
        self.assertNotIn("actions/checkout", APPROVAL_WORKFLOW)

    def test_an_unevaluated_acknowledgement_is_not_reported_as_missing(self):
        # The detector that reads the description lives in pr-validation. Where
        # it did not run, the state is unknown — and "missing" would send the
        # author after a line no check is asking for.
        rendered = render_reporter("waiting", ACKNOWLEDGED="")
        self.assertNotIn("Author acknowledgement", rendered)
        rendered = render_reporter("waiting", ACKNOWLEDGED="false")
        self.assertIn("Author acknowledgement", rendered)
        self.assertIn("missing", rendered)

    def test_the_fact_label_outlives_the_decision(self):
        # Run it, per state, and read the `gh pr edit` calls. Asserting on the
        # composite's text cannot tell which state made which call: moving
        # `--add-label "$LABEL"` into the `waiting` branch would leave every
        # string in place and stop the fact label from surviving a decision.
        for state in ("waiting", "approved", "rejected", "acknowledgement"):
            with self.subTest(state=state):
                calls = run_reporter_labels(state)
                pairs = list(zip(calls[::2], calls[1::2]))

                self.assertIn(
                    ("add-label", "breaking-change"),
                    pairs,
                    "the fact label belongs on every state the gate reports",
                )
                self.assertNotIn(
                    ("remove-label", "breaking-change"),
                    pairs,
                    "approving does not make the break go away",
                )

                expected = "add-label" if state == "waiting" else "remove-label"
                self.assertIn((expected, "awaiting-breaking-approval"), pairs)

    def test_the_two_labels_can_be_turned_off_independently(self):
        # Cosmetic throughout: a repository that declared neither still gets
        # its gate, and one that wants only the fact can say so.
        self.assertEqual([], run_reporter_labels("waiting", LABEL="", PENDING_LABEL=""))
        self.assertEqual(
            ["add-label", "breaking-change"],
            run_reporter_labels("waiting", PENDING_LABEL=""),
        )

    def test_the_fact_label_goes_only_when_the_break_does(self):
        # `state=none` is reached two ways and they are not the same fact. The
        # previous assertion pinned the loop that removed both labels in both
        # cases — describing the code, which is how a loop taking off a true
        # label stayed green. Run it instead, and read the calls.
        def labels_removed(**overrides):
            result, outputs = run_verdict(
                LABEL="breaking-change",
                PENDING_LABEL="awaiting-breaking-approval",
                **overrides,
            )
            self.assertEqual("none", outputs["state"])
            return {
                call.rsplit(" ", 1)[-1]
                for call in result.gh_calls
                if "--remove-label" in call
            }

        # Out of scope with the break still there. The acknowledgement reporter
        # has just applied `breaking-change` because the break is real and the
        # author still has to declare it — taking it back off here was the gate
        # undoing its own correct labelling.
        self.assertEqual(
            {"awaiting-breaking-approval"},
            labels_removed(IN_SCOPE="false", HAS_BREAKING_CHANGES="true"),
        )

        # The break actually gone — a reword dropping the `!`. Now the fact
        # stopped being true, so both come off.
        self.assertEqual(
            {"awaiting-breaking-approval", "breaking-change"},
            labels_removed(IN_SCOPE="true", HAS_BREAKING_CHANGES="false"),
        )

    def test_the_acknowledgement_line_survives_the_decision(self):
        # The approval and the acknowledgement are different controls. A
        # reviewer saying yes to a break is not the author declaring it, and
        # Blocking Checks keeps failing until the line is in the description.
        #
        # The instructions used to live in `waiting` alone, so the approval
        # rewrote the comment and took the only copy with it: red check, no
        # instructions, nothing on the pull request saying what to paste.
        line = "Breaking change acknowledged: I understand ..."
        for state in ("waiting", "approved", "blocked"):
            rendered = render_reporter(state, ACKNOWLEDGED="false", ACK_LINE=line)
            self.assertIn("Add this exact line", rendered, state)
            self.assertIn(line, rendered, state)

        # And it goes away once the line is there — it is remediation, not
        # decoration.
        done = render_reporter("approved", ACKNOWLEDGED="true", ACK_LINE=line)
        self.assertNotIn("Add this exact line", done)

        # The outcome job has to forward the literal, or there is nothing to
        # print no matter what the renderer does.
        workflow = yaml.safe_load(APPROVAL_WORKFLOW)
        step = next(
            s
            for s in workflow["jobs"]["outcome"]["steps"]
            if s.get("name") == "Report the outcome on the pull request"
        )
        self.assertIn("author-acknowledgement", step["with"])

    def test_no_instruction_is_better_than_an_empty_one(self):
        # `author-acknowledgement` is empty by default, so a direct caller on
        # the composite's defaults was told to "add this exact line" above an
        # empty code block. The waiting branch already checked; this one did
        # not.
        rendered = render_reporter("acknowledgement", ACKNOWLEDGED="false", ACK_LINE="")
        self.assertNotIn("Add this exact line", rendered)
        self.assertNotIn("```", rendered)
        # The break is still announced — only the unusable instruction is gone.
        self.assertIn("acknowledgement missing", rendered)

    def test_a_blocked_gate_says_so_on_the_pull_request(self):
        # Detection failing fails the check. It used to do that silently: a red
        # check with no comment reads as a flake and gets re-run rather than
        # looked at.
        rendered = render_reporter("blocked", ACKNOWLEDGED="")
        self.assertIn("could not run", rendered)
        self.assertIn("fails closed", rendered)

        workflow = yaml.safe_load(APPROVAL_WORKFLOW)
        step = next(
            s
            for s in workflow["jobs"]["outcome"]["steps"]
            if s.get("name") == "Report the outcome on the pull request"
        )
        self.assertIn("'blocked'", step["if"])

    def test_disabling_approval_keeps_the_acknowledgement_feedback(self):
        # `enable_breaking_change_approval: false` turns off the human
        # approval, not the acknowledgement — Blocking Checks still fails
        # without the line. Skipping the whole job took the only comment
        # carrying that line with it.
        validation = yaml.safe_load(
            (REPO_ROOT / ".github" / "workflows" / "pr-validation.yml").read_text(
                encoding="utf-8"
            )
        )
        job = validation["jobs"]["breaking-change-approval"]
        self.assertNotIn("inputs.enable_breaking_change_approval", job["if"])
        self.assertEqual(
            "${{ inputs.enable_breaking_change_approval }}",
            job["with"]["enable_approval"],
        )

        # The gate treats it as out of scope for the approval and nothing more,
        # so no Environment is ever touched.
        approval = yaml.safe_load(APPROVAL_WORKFLOW)
        in_scope = approval["jobs"]["detect"]["outputs"]["in-scope"]
        self.assertIn("inputs.enable_approval", in_scope)

        # And the published result still says `skipped`, not `success`: the job
        # runs now, but nothing was approved.
        result = validation[True]["workflow_call"]["outputs"][
            "breaking_change_approval_result"
        ]["value"]
        self.assertIn("!inputs.enable_breaking_change_approval && 'skipped'", result)

    def test_the_historical_approver_survives_a_reused_approval(self):
        # Reuse skips the approval job, so the current run holds no Environment
        # decision and `decisions` comes back empty. Without the fallback the
        # comment degrades to "Approved by a reviewer" on the next push, losing
        # the name of whoever actually decided.
        workflow = yaml.safe_load(APPROVAL_WORKFLOW)
        request = workflow["jobs"]["request"]
        self.assertIn("approved-by", request["outputs"])

        step = next(
            s
            for s in workflow["jobs"]["outcome"]["steps"]
            if s.get("name") == "Report the outcome on the pull request"
        )
        self.assertIn(
            "needs.request.outputs.approved-by", step["with"]["approvers"]
        )
        # And it is the verified identity, not one read from the comment: the
        # lookup only sets it after the Environment log confirms the run.
        lookup = extract_step(
            extract_job(APPROVAL_WORKFLOW, "request"),
            "Check for a prior approval of the same change",
        )
        verified_at = lookup.index('approved_by="$approvers"')
        guard_at = lookup.index('select(.state == "approved")')
        self.assertLess(guard_at, verified_at)

    def test_the_fingerprint_comes_from_the_breaking_commits(self):
        detect = extract_job(APPROVAL_WORKFLOW, "detect")
        self.assertIn("src/validate/breaking-change-commits@", detect)
        self.assertIn("fingerprint: ${{ steps.commits.outputs.fingerprint }}", detect)

    def test_the_verdict_states_are_reachable_as_documented(self):
        # The whole table in one place, run rather than read.
        for description, env, expected in (
            ("approved", {"APPROVAL_RESULT": "success"}, "approved"),
            (
                "rejected",
                {"APPROVAL_RESULT": "failure", "REJECTERS": "dave"},
                "rejected",
            ),
            (
                "cancelled, same head, a newer run carries it",
                {"APPROVAL_RESULT": "cancelled", "MOCK_NEWER_RUNS": "1"},
                "superseded",
            ),
            (
                "cancelled, same head, nothing replacing it",
                {"APPROVAL_RESULT": "cancelled", "MOCK_NEWER_RUNS": "0"},
                "unresolved",
            ),
            (
                "head moved under us",
                {"LIVE_SHA": "def456"},
                "superseded",
            ),
            (
                "failed with no recorded decision",
                {"APPROVAL_RESULT": "failure"},
                "unresolved",
            ),
            ("nothing to approve", {"HAS_BREAKING_CHANGES": "false"}, "none"),
            (
                "detection never completed",
                {"DETECTION_SUCCEEDED": "false"},
                "blocked",
            ),
        ):
            with self.subTest(case=description):
                _, outputs = run_verdict(**env)
                self.assertEqual(expected, outputs["state"])
        # And `superseded` must drive neither the comment nor the close.
        for step_name in (
            "Report the outcome on the pull request",
            "Close the pull request on rejection",
        ):
            with self.subTest(step=step_name):
                step = extract_step(extract_job(APPROVAL_WORKFLOW, "outcome"), step_name)
                self.assertNotIn("superseded", step)

    def test_the_environment_is_read_exactly_once(self):
        # Two reads would allow "rules fetched, reviewers not" — and an empty
        # reviewer list is indistinguishable from "this Environment has none",
        # so a caller would fall back to whoever it had configured and name the
        # wrong people. One read, both answers, no such state.
        reads = ENVIRONMENT_PROTECTION.count(
            'gh api "repos/${REPO}/environments/${ENVIRONMENT}"'
        )
        self.assertEqual(1, reads, "the Environment must be read exactly once")
        self.assertIn("reviewers_of()", ENVIRONMENT_PROTECTION)
        self.assertIn("rules_of()", ENVIRONMENT_PROTECTION)

    def test_the_button_degrades_when_the_badge_cannot_load(self):
        reporter = (
            REPO_ROOT / "src" / "notify" / "breaking-change-approval-reporter"
            / "action.yml"
        ).read_text(encoding="utf-8")
        # The badge is an external image. Its alt text carries the whole call to
        # action, so a blocked image leaves a described link, not a broken box.
        self.assertIn("[![Review the pending deployment]", reporter)
        # And an empty badge-url falls back to a plain heading link.
        self.assertIn('elif [ -n "$RUN_URL" ]; then', reporter)

    # GitHub alerts colour the block and supply the icon; the emoji marks what
    # the block is about, so the state is readable from the timeline without
    # opening anything.
    STATE_MARKS = (
        ("waiting", "[!IMPORTANT]", "## 💥 Breaking change detected"),
        ("approved", "[!NOTE]", "## ✅ Breaking change approved"),
        ("rejected", "[!CAUTION]", "## ⛔ Breaking change rejected"),
        ("unresolved", "[!WARNING]", "## 💥 Breaking change — decision not recorded"),
    )

    def test_each_state_renders_its_own_alert_and_mark(self):
        # Rendered, not grepped. Asserting against the source only proves a
        # string exists somewhere in it, so swapping two states' alerts would
        # keep every assertion green while every comment said the wrong thing.
        for state, alert, mark in self.STATE_MARKS:
            with self.subTest(state=state):
                rendered = render_reporter(state)
                # As adjacent blockquote lines, not as two strings that happen
                # to be somewhere: a GitHub alert only renders inside `>`, so
                # dropping the quote would leave both assertions green and the
                # comment looking like plain text.
                self.assertIn(f"> {alert}\n> {mark}", rendered)

                # Exclusivity is what actually catches a swap.
                for other_state, other_alert, other_mark in self.STATE_MARKS:
                    if other_state == state:
                        continue
                    self.assertNotIn(other_alert, rendered)
                    self.assertNotIn(other_mark, rendered)

    def test_the_undo_example_uses_the_real_commit_subjects(self):
        reporter = (
            REPO_ROOT / "src" / "notify" / "breaking-change-approval-reporter"
            / "action.yml"
        ).read_text(encoding="utf-8")
        self.assertIn('repos/${REPO}/pulls/${PR_NUMBER}/commits', reporter)
        self.assertIn("```diff", reporter)
        # A view, never a verdict: with no subject matched it must fall back to
        # generic wording rather than invent an example.
        self.assertIn('if [ -n "$breaking_subjects" ]; then', reporter)

    def test_a_missing_environment_is_told_apart_from_an_unreadable_one(self):
        # Creating on top of a 403 would be guessing; only a 404 is ours to fix.
        self.assertIn('*"HTTP 404"* | *"Not Found"* )', ENVIRONMENT_PROTECTION)

    def test_approvals_composite_reports_whether_it_could_read(self):
        # Empty lists mean "nobody decided" only when the API was readable.
        # Without this flag a 403 would be indistinguishable from an approval
        # that never happened.
        self.assertIn("api-readable:", ENVIRONMENT_APPROVALS)
        self.assertIn("api_readable=false", ENVIRONMENT_APPROVALS)
        self.assertIn('|| [ -n "$state" ]', ENVIRONMENT_APPROVALS)

    def test_outcome_does_not_escalate_permissions(self):
        job = extract_job(APPROVAL_WORKFLOW, "outcome")
        permissions = extract_mapping_entry(job, "permissions", indent=4)
        # A called workflow may only request permissions the caller already holds,
        # so declaring `actions: read` here would break every consumer whose
        # entrypoint does not grant it. Scoped to the `permissions:` block —
        # the step text mentions it on purpose, explaining the fallback.
        self.assertNotIn("actions:", permissions)
        self.assertIn("pull-requests: write", permissions)

    def test_pull_request_is_closed_only_on_a_recorded_rejection(self):
        job = extract_job(APPROVAL_WORKFLOW, "outcome")
        step = extract_step(job, "Close the pull request on rejection")
        # Gated on the resolved state, never on the raw job conclusion: a
        # cancelled run must not close a pull request.
        self.assertIn(
            "if: steps.verdict.outputs.state == 'rejected'"
            " && inputs.close_on_rejection && !inputs.dry_run",
            step,
        )
        body = extract_run_body(job, "Resolve the verdict")
        self.assertIn('state=rejected', body)
        # `rejected` is only reachable from a recorded rejecter, or from a failed
        # approval job when the approvals API could not be read at all.
        self.assertIn('"$API_READABLE" != "true" ]', body)
        self.assertIn('"$APPROVAL_RESULT" = "failure"', body)

    def test_pr_validation_hands_detection_over_and_fails_closed(self):
        job = extract_job(WORKFLOW, "breaking-change-approval")
        self.assertIn("uses: ./.github/workflows/breaking-change-approval.yml", job)
        self.assertIn("inputs.enable_breaking_change_approval", job)
        # `unknown` rather than the normalised `false`: a detection that did not
        # complete must not read as "no breaking changes".
        self.assertIn("|| 'unknown'", job)
        self.assertIn(
            "needs.breaking-change-guard.outputs.detection-succeeded == 'true'", job
        )

    def test_approval_gate_is_a_side_branch_of_the_validation_graph(self):
        # Nothing may depend on it: a pull request waiting days for its approval
        # must still get its title, source-branch and signature verdicts.
        for job_id in (
            "blocking-checks",
            "advisory-checks",
            "pr-checks-summary",
            "pr-validation-report",
        ):
            with self.subTest(job=job_id):
                job = extract_job(WORKFLOW, job_id)
                self.assertNotIn("breaking-change-approval", job)

    def test_umbrellas_forward_every_approval_gate_input(self):
        for name, text in (("go", GO_WORKFLOW), ("js", JS_WORKFLOW)):
            for key in sorted(APPROVAL_GATE_INPUTS):
                with self.subTest(workflow=name, input=key):
                    self.assertIn(f"{key}: ${{{{ inputs.{key} }}}}", text)

    def test_self_validation_states_the_gate_explicitly(self):
        self.assertIn("enable_breaking_change_approval: true", SELF_WORKFLOW)


class ActionMetadataTests(unittest.TestCase):
    def test_reporter_and_summary_keep_backward_compatible_guard_defaults(self):
        for name, text in (("reporter", REPORTER), ("summary", SUMMARY)):
            inputs = extract_top_level_section(text, "inputs")
            with self.subTest(action=name, input="breaking-change-result"):
                entry = extract_mapping_entry(inputs, "breaking-change-result")
                self.assertIn("required: false", entry)
                self.assertRegex(entry, r'(?m)^    default: ["\']?skipped["\']?$')
            with self.subTest(action=name, input="blocking-checks-result"):
                entry = extract_mapping_entry(inputs, "blocking-checks-result")
                self.assertIn("required: false", entry)
                self.assertRegex(entry, r'(?m)^    default: ["\']?skipped["\']?$')

    def test_reporter_and_summary_expose_deterministic_state_outputs(self):
        for name, text in (("reporter", REPORTER), ("summary", SUMMARY)):
            outputs = extract_top_level_section(text, "outputs")
            with self.subTest(action=name, output="guard"):
                entry = extract_mapping_entry(outputs, "has-breaking-change-guard")
                self.assertIn(
                    "value: ${{ steps.guard-state.outputs.has-breaking-change-guard }}",
                    entry,
                )
            with self.subTest(action=name, output="blocking"):
                entry = extract_mapping_entry(
                    outputs, "has-blocking-checks-runtime-failure"
                )
                self.assertIn(
                    "value: ${{ steps.guard-state.outputs.has-blocking-checks-runtime-failure }}",
                    entry,
                )

            state_step = extract_step(text, "Resolve breaking change guard state")
            for key in (
                "has-breaking-change-guard=true",
                "has-breaking-change-guard=false",
                "has-blocking-checks-runtime-failure=true",
                "has-blocking-checks-runtime-failure=false",
            ):
                self.assertIn(key, state_step)


class SelfValidationTests(unittest.TestCase):
    def test_workflow_regression_suite_runs_unconditionally_with_detector_matrix(self):
        job = extract_job(SELF_WORKFLOW, "breaking-change-guard-tests")
        self.assertNotRegex(job, r"(?m)^    (?:if|needs):")
        detector = "run: bash src/validate/breaking-change-guard/test.sh"
        workflow = "run: python3 src/validate/breaking-change-guard/test-workflow.py"
        self.assertIn(detector, job)
        self.assertIn(workflow, job)
        self.assertLess(job.index(detector), job.index(workflow))

    def test_self_validation_job_stays_secretless_and_contents_read(self):
        job = extract_job(SELF_WORKFLOW, "breaking-change-guard-tests")
        self.assertRegex(job, r"(?m)^    permissions:\n      contents: read$")
        self.assertNotIn("secrets:", job)
        self.assertNotIn("github.token", job)
        checkout = extract_step(job, "Checkout")
        self.assertIn("persist-credentials: false", checkout)

    def test_readme_documents_both_local_guard_test_commands(self):
        self.assertIn("bash src/validate/breaking-change-guard/test.sh", README)
        self.assertIn(
            "python3 src/validate/breaking-change-guard/test-workflow.py", README
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
