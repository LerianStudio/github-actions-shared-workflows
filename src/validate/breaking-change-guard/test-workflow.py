#!/usr/bin/env python3

import os
import re
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "pr-validation.yml"
SELF_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "self-pr-validation.yml"
GO_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "go-pr-validation.yml"
JS_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "js-pr-validation.yml"
REPORTER_PATH = REPO_ROOT / "src" / "notify" / "pr-validation-reporter" / "action.yml"
SUMMARY_PATH = REPO_ROOT / "src" / "validate" / "pr-checks-summary" / "action.yml"
README_PATH = REPO_ROOT / "src" / "validate" / "breaking-change-guard" / "README.md"

WORKFLOW = WORKFLOW_PATH.read_text(encoding="utf-8")
SELF_WORKFLOW = SELF_WORKFLOW_PATH.read_text(encoding="utf-8")
GO_WORKFLOW = GO_WORKFLOW_PATH.read_text(encoding="utf-8")
JS_WORKFLOW = JS_WORKFLOW_PATH.read_text(encoding="utf-8")
REPORTER = REPORTER_PATH.read_text(encoding="utf-8")
SUMMARY = SUMMARY_PATH.read_text(encoding="utf-8")
README = README_PATH.read_text(encoding="utf-8")

ACKNOWLEDGEMENT = (
    "Breaking change acknowledged: I understand that this PR intentionally "
    "introduces a breaking change and requires the next release to be a major version."
)


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
        self.assertFalse(
            any("breaking" in key or "acknowledgement" in key for key in keys)
        )

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
        detector_step = extract_step(
            extract_job(WORKFLOW, "breaking-change-guard"), "Detect breaking changes"
        )
        comment_job = extract_job(WORKFLOW, "breaking-change-comment")
        detector_literal = re.search(
            r"(?m)^\s*breaking-change-acknowledgement: '(?P<value>[^']*)'$",
            detector_step,
        )
        comment_literal = re.search(
            r"(?m)^\s*ACKNOWLEDGEMENT: '(?P<value>[^']*)'$", comment_job
        )
        self.assertIsNotNone(detector_literal)
        self.assertIsNotNone(comment_literal)
        self.assertEqual(ACKNOWLEDGEMENT, detector_literal.group("value"))
        self.assertEqual(
            detector_literal.group("value"), comment_literal.group("value")
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

    def test_comment_job_is_write_minimal_and_does_not_checkout(self):
        job = extract_job(WORKFLOW, "breaking-change-comment")
        permissions = re.search(
            r"(?m)^    permissions:\n(?P<body>(?:      [^\n]+\n?)+)", job
        )
        self.assertIsNotNone(permissions)
        self.assertEqual(
            {"pull-requests: read", "issues: write"},
            {line.strip() for line in permissions.group("body").splitlines()},
        )
        self.assertNotIn("contents:", permissions.group("body"))
        self.assertNotIn("actions/checkout", job)
        self.assertIn("github-token: ${{ github.token }}", job)

    def test_comment_job_owns_only_exact_bot_marker_comments(self):
        job = extract_job(WORKFLOW, "breaking-change-comment")
        self.assertIn("comment.user?.login === 'github-actions[bot]'", job)
        self.assertIn("comment.body === marker", job)
        self.assertIn("comment.body?.startsWith(`${marker}\\n`)", job)
        self.assertNotIn("comment.body?.includes(marker)", job)
        self.assertEqual(2, job.count("const body = `${marker}\\n"))

    def test_comment_job_uses_author_acknowledgement_not_authorization(self):
        job = extract_job(WORKFLOW, "breaking-change-comment")
        self.assertIn("'✅ Author acknowledged'", job)
        self.assertIn("'🚫 Awaiting author acknowledgement'", job)
        self.assertIn("does not grant maintainer permission", job)
        self.assertNotIn("'✅ Approved'", job)
        self.assertNotIn("'🚫 Awaiting approval'", job)

    def test_comment_job_rejects_stale_head_updates(self):
        job = extract_job(WORKFLOW, "breaking-change-comment")
        self.assertIn("EVENT_HEAD_SHA: ${{ github.event.pull_request.head.sha }}", job)
        self.assertIn("github.rest.pulls.get", job)
        self.assertIn("current.data.head.sha !== eventHeadSha", job)

    def test_comment_job_reconciles_detector_failure(self):
        job = extract_job(WORKFLOW, "breaking-change-comment")
        self.assertIn("if (!guardJobSucceeded || !detectionSucceeded)", job)
        self.assertIn("**Status:** ⚠️ Detection failed", job)
        self.assertIn("Blocking Checks failed closed.", job)
        failure_branch = job.index("if (!guardJobSucceeded || !detectionSucceeded)")
        no_breaking_branch = job.index("if (!hasBreakingChanges)")
        self.assertIn(
            "await upsertOwned(body);", job[failure_branch:no_breaking_branch]
        )

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
                self.assertFalse(
                    any(
                        "breaking" in key or "acknowledgement" in key
                        for key in input_keys
                    ),
                    input_keys,
                )


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
