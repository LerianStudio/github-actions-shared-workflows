#!/usr/bin/env python3

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
    }
    env.update(overrides)

    with tempfile.TemporaryDirectory() as stub_dir:
        stub = Path(stub_dir) / "gh"
        stub.write_text(
            "#!/usr/bin/env bash\n"
            "case \"$*\" in\n"
            "  *\"/commits\"*) printf '%s\\n'"
            " 'feat(scope)!: a breaking subject' 'chore: an ordinary one' ;;\n"
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
    }
    env.update(overrides)

    with tempfile.TemporaryDirectory() as temp_dir:
        stub = Path(temp_dir) / "gh"
        stub.write_text(
            "#!/usr/bin/env bash\n"
            'case "$*" in\n'
            '  *headRefOid*) printf \'%s\\n\' "$LIVE_SHA" ;;\n'
            "  *) exit 1 ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        stub.chmod(0o755)
        output_path = Path(temp_dir) / "github-output"
        output_path.touch()
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
        return result, parse_github_output(output_path.read_text(encoding="utf-8"))


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
        # Explicit reviewers win; CODEOWNERS is the fallback.
        preflight = extract_step(
            extract_job(APPROVAL_WORKFLOW, "request"),
            "Verify the breaking-approval Environment is protected",
        )
        self.assertIn(
            "inputs.approval_reviewers != '' && inputs.approval_reviewers"
            " || steps.codeowners.outputs.reviewers",
            preflight,
        )

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
        # would ping the whole team again for the same thing. Checked on the
        # rendered comment, so it holds however the composite spells it.
        for match in re.finditer(r"@LerianStudio/", rendered):
            self.assertTrue(
                rendered[: match.start()].endswith("["),
                f"bare team mention: ...{rendered[max(0, match.start() - 40):match.end() + 30]}...",
            )

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
        self.assertIn('if [ "$APPROVAL_RESULT" = "cancelled" ]; then', body)
        cancelled_at = body.index('"$APPROVAL_RESULT" = "cancelled"')
        head_compare_at = body.index('"$live_sha" != "$HEAD_SHA"')
        self.assertLess(
            cancelled_at,
            head_compare_at,
            "the cancelled check must come first — it is the broader signal",
        )

    def test_a_cancelled_approval_stops_before_anything_can_act_on_it(self):
        # Run it, with a recorded rejection sitting right there. The branch has
        # to stop: if it falls through, the rejection downstream wins, the
        # verdict comes back `rejected`, and the pull request gets closed —
        # because a concurrency cancellation raced a reviewer.
        _, outputs = run_verdict(APPROVAL_RESULT="cancelled", REJECTERS="dave")
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
        self.assertIn("steps.prior.outputs.already-approved != 'true'", step)

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
                for match in re.finditer(rf"@{who}", rendered):
                    self.assertTrue(rendered[: match.start()].endswith("["))

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
        # Every diagnostic beyond the single summary sits behind the dry-run
        # branch; count them to keep a future one from slipping out.
        for line in code.splitlines():
            if "echo " not in line or "GITHUB_OUTPUT" in line:
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

    def test_the_records_are_never_rewritten_blind(self):
        reporter = (
            REPO_ROOT / "src" / "notify" / "breaking-change-approval-reporter"
            / "action.yml"
        ).read_text(encoding="utf-8")
        # A failed read must not look like "there were none": the rewrite would
        # erase approvals already given.
        self.assertIn("Refusing to rewrite it", reporter)
        self.assertIn("if ! current_body=$(gh api", reporter)

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

    def test_both_labels_go_when_the_break_does(self):
        body = extract_run_body(
            extract_job(APPROVAL_WORKFLOW, "outcome"), "Resolve the verdict"
        )
        # The one moment the fact stops being true. This cleanup was lost in an
        # earlier rewrite, leaving `breaking-change` on a pull request whose
        # breaking commit had been reworded away.
        self.assertIn('for stale in "$LABEL" "$PENDING_LABEL"', body)
        none_at = body.index("state=none")
        cleanup_at = body.index('for stale in "$LABEL" "$PENDING_LABEL"')
        self.assertLess(none_at, cleanup_at)

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
                "cancelled, same head",
                {"APPROVAL_RESULT": "cancelled"},
                "superseded",
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
