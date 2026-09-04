#!/usr/bin/env python3

"""Behavioural tests for the `outdated-non-blocking` advisory path.

Two layers:

  * `AdvisoryVerdictTests` runs the composite's comparison step for real. The
    fixtures pin every library through `.lerianstudiolibignore`, which makes the
    composite skip the releases API entirely — so the tests are hermetic and need
    no network, no token and no jq.

  * `AdvisoryConditionTests` and `DocumentationMatrixTests` assert the umbrella's
    matching rule as text, then evaluate the documented branch matrix. The
    expression itself is asserted verbatim first, so the Python mirror below
    cannot drift away from the workflow silently.
"""

import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ACTION_PATH = REPO_ROOT / "src" / "validate" / "lerian-lib-version" / "action.yml"
CHECK_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "lerian-lib-version-check.yml"
GO_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "go-pr-validation.yml"
DOCS_PATH = REPO_ROOT / "docs" / "go-pr-validation.md"

ACTION = ACTION_PATH.read_text(encoding="utf-8")
CHECK_WORKFLOW = CHECK_WORKFLOW_PATH.read_text(encoding="utf-8")
GO_WORKFLOW = GO_WORKFLOW_PATH.read_text(encoding="utf-8")
DOCS = DOCS_PATH.read_text(encoding="utf-8")

COMPARE_STEP = "Parse Lerian dependencies, resolve latest releases, compare"
GO_MOD_STEP = "Verify go.mod exists"

ADVISORY_INPUT = "lib_version_non_blocking_for_hotfix_to_main"

# The composite uses `declare -A`, which needs bash 4+. macOS ships bash 3.2 as
# /bin/bash, so resolve a modern one from PATH and skip rather than fail there.
def _modern_bash():
    for candidate in ("bash", "/opt/homebrew/bin/bash", "/usr/local/bin/bash", "/bin/bash"):
        path = shutil.which(candidate) if "/" not in candidate else candidate
        if not path or not os.path.exists(path):
            continue
        try:
            out = subprocess.run(
                [path, "-c", "echo ${BASH_VERSINFO[0]}"],
                capture_output=True, text=True, check=True,
            ).stdout.strip()
        except (subprocess.CalledProcessError, OSError):
            continue
        if out.isdigit() and int(out) >= 4:
            return path
    return None


BASH = _modern_bash()


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
    for line in lines[start + 1:]:
        if line.strip() and indentation(line) <= run_indent:
            break
        body.append(line[run_indent + 2:] if len(line) > run_indent else "")
    return "\n".join(body)


COMPARE_SCRIPT = extract_run_body(ACTION, COMPARE_STEP)
GO_MOD_SCRIPT = extract_run_body(ACTION, GO_MOD_STEP)


class ScriptRunner:
    """Runs an extracted composite step against a throwaway workspace."""

    def __init__(self, testcase):
        self.dir = Path(tempfile.mkdtemp(prefix="lerian-lib-version-"))
        testcase.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def write(self, name, content):
        target = self.dir / name
        target.write_text(content, encoding="utf-8")
        return target

    def run(self, script, **env_overrides):
        outputs = self.dir / "github_output"
        summary = self.dir / "github_step_summary"
        outputs.touch()
        summary.touch()

        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(self.dir),
            "GITHUB_OUTPUT": str(outputs),
            "GITHUB_STEP_SUMMARY": str(summary),
            "RUNNER_TEMP": str(self.dir),
            "GO_MOD_PATH": "go.mod",
            "IGNORE_FILE": ".lerianstudiolibignore",
            "CHECK_INDIRECT": "false",
            "GRACE_DAYS": "0",
            "OUTDATED_NON_BLOCKING": "false",
            "DRY_RUN": "false",
            "GH_TOKEN": "unused-because-every-lib-is-pinned",
        }
        env.update(env_overrides)

        result = subprocess.run(
            [BASH, "-c", script],
            cwd=self.dir, env=env, capture_output=True, text=True,
        )
        result.github_output = outputs.read_text(encoding="utf-8")
        result.step_summary = summary.read_text(encoding="utf-8")
        return result


# A pinned lib is compared against the pin and never reaches the releases API,
# which is what keeps these tests hermetic.
GO_MOD_OUTDATED = """module github.com/LerianStudio/example

go 1.23

require (
\tgithub.com/LerianStudio/lib-commons/v5 v5.1.0
)
"""

GO_MOD_CURRENT = GO_MOD_OUTDATED.replace("v5.1.0", "v5.9.0")

GO_MOD_NO_LERIAN_LIBS = """module github.com/LerianStudio/example

go 1.23

require (
\tgithub.com/stretchr/testify v1.9.0
)
"""

IGNORE_PIN = "lib-commons/v5@v5.9.0\n"


@unittest.skipUnless(BASH, "requires bash 4+ for the composite's associative arrays")
class AdvisoryVerdictTests(unittest.TestCase):
    def setUp(self):
        self.runner = ScriptRunner(self)

    def _outdated_workspace(self):
        self.runner.write("go.mod", GO_MOD_OUTDATED)
        self.runner.write(".lerianstudiolibignore", IGNORE_PIN)

    def test_outdated_lib_fails_when_blocking(self):
        self._outdated_workspace()
        result = self.runner.run(COMPARE_SCRIPT, OUTDATED_NON_BLOCKING="false")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("::error title=Outdated Lerian libraries", result.stdout)

    def test_outdated_lib_is_advisory_when_non_blocking(self):
        self._outdated_workspace()
        result = self.runner.run(COMPARE_SCRIPT, OUTDATED_NON_BLOCKING="true")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("::warning title=Outdated Lerian libraries", result.stdout)
        self.assertNotIn("::error title=Outdated Lerian libraries", result.stdout)

    def test_advisory_report_is_marked_and_still_asks_for_the_bump(self):
        self._outdated_workspace()
        result = self.runner.run(COMPARE_SCRIPT, OUTDATED_NON_BLOCKING="true")
        self.assertIn("outdated (advisory)", result.step_summary)
        self.assertIn("Advisory on this pull request", result.step_summary)
        self.assertIn("Bump the outdated libraries", result.step_summary)

    def test_advisory_still_reports_the_outdated_state_to_callers(self):
        """The gate goes green, but has_outdated must stay true — that is the
        'expose the outdated result as advisory information' half of the ask."""
        self._outdated_workspace()
        result = self.runner.run(COMPARE_SCRIPT, OUTDATED_NON_BLOCKING="true")
        self.assertIn("has_outdated=true", result.github_output)
        self.assertIn("outdated_count=1", result.github_output)

    def test_blocking_report_is_not_marked_advisory(self):
        self._outdated_workspace()
        result = self.runner.run(COMPARE_SCRIPT, OUTDATED_NON_BLOCKING="false")
        self.assertIn("action required", result.step_summary)
        self.assertNotIn("advisory", result.step_summary.lower())

    def test_up_to_date_lib_passes_under_advisory(self):
        self.runner.write("go.mod", GO_MOD_CURRENT)
        self.runner.write(".lerianstudiolibignore", IGNORE_PIN)
        result = self.runner.run(COMPARE_SCRIPT, OUTDATED_NON_BLOCKING="true")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("has_outdated=false", result.github_output)

    # ----------------- The exception must not widen -----------------

    def test_no_lerian_libs_still_fails_under_advisory(self):
        self.runner.write("go.mod", GO_MOD_NO_LERIAN_LIBS)
        self.runner.write(".lerianstudiolibignore", IGNORE_PIN)
        result = self.runner.run(COMPARE_SCRIPT, OUTDATED_NON_BLOCKING="true")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("::error title=No Lerian libraries found", result.stdout)

    def test_missing_go_mod_still_fails_under_advisory(self):
        result = self.runner.run(GO_MOD_SCRIPT, OUTDATED_NON_BLOCKING="true")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("::error title=go.mod not found", result.stdout)

    def test_go_mod_guard_cannot_be_softened_at_all(self):
        self.assertNotIn("OUTDATED_NON_BLOCKING", GO_MOD_SCRIPT)


# ----------------- Matching rule (umbrella workflow) -----------------

EXPECTED_CONDITION = (
    "${{ inputs.lib_version_non_blocking_for_hotfix_to_main "
    "&& github.base_ref == 'main' "
    "&& startsWith(github.head_ref, 'hotfix/') }}"
)


def is_advisory(enabled, base_ref, head_ref):
    """Mirror of EXPECTED_CONDITION. Asserted against the workflow verbatim in
    test_condition_is_exactly_the_documented_one, so it cannot drift."""
    return bool(enabled and base_ref == "main" and head_ref.startswith("hotfix/"))


class AdvisoryConditionTests(unittest.TestCase):
    def setUp(self):
        match = re.search(r"^\s*outdated_non_blocking:\s*(.+)$", GO_WORKFLOW, re.MULTILINE)
        self.assertIsNotNone(match, "umbrella does not forward outdated_non_blocking")
        self.condition = match.group(1).strip()

    def test_condition_is_exactly_the_documented_one(self):
        self.assertEqual(self.condition, EXPECTED_CONDITION)

    def test_input_defaults_to_current_blocking_behaviour(self):
        block = re.search(
            rf"^      {ADVISORY_INPUT}:\n(?:.*\n)*?        default: (\S+)$",
            GO_WORKFLOW, re.MULTILINE,
        )
        self.assertIsNotNone(block, f"{ADVISORY_INPUT} input not declared")
        self.assertEqual(block.group(1), "false")

    def test_nested_workflow_input_defaults_to_blocking(self):
        block = re.search(
            r"^      outdated_non_blocking:\n(?:.*\n)*?        default: (\S+)$",
            CHECK_WORKFLOW, re.MULTILINE,
        )
        self.assertIsNotNone(block, "outdated_non_blocking input not declared")
        self.assertEqual(block.group(1), "false")

    def test_gate_does_not_soften_the_result(self):
        """The exception belongs inside the check. A job result cannot tell an
        outdated dependency from a failed checkout, so softening it at the
        aggregator would swallow infrastructure failures too."""
        gate = GO_WORKFLOW.split("lib-version-gate:", 1)[1]
        gate = gate.split("\n  permission-manifest-nudge:", 1)[0]
        self.assertNotIn(ADVISORY_INPUT, gate)
        self.assertNotIn("outdated_non_blocking", gate)

    def test_gate_still_propagates_change_detection_failures(self):
        gate = GO_WORKFLOW.split("lib-version-gate:", 1)[1]
        gate = gate.split("\n  permission-manifest-nudge:", 1)[0]
        self.assertIn("needs.changes.result != 'success' && needs.changes.result", gate)

    # ----------------- Branch matrix -----------------

    def test_matching_hotfix_to_main_is_advisory_only_when_enabled(self):
        self.assertTrue(is_advisory(True, "main", "hotfix/urgent-fix"))
        self.assertFalse(is_advisory(False, "main", "hotfix/urgent-fix"))

    def test_non_matching_branch_combinations_stay_blocking(self):
        for enabled, base, head in (
            (True, "develop", "hotfix/urgent-fix"),
            (True, "release-candidate", "hotfix/urgent-fix"),
            (True, "main", "develop"),
            (True, "main", "feat/new-thing"),
            (True, "main", "fix/not-a-hotfix"),
            (True, "main", "release-candidate"),
            (False, "develop", "hotfix/urgent-fix"),
            (False, "main", "feat/new-thing"),
        ):
            with self.subTest(enabled=enabled, base=base, head=head):
                self.assertFalse(is_advisory(enabled, base, head))

    def test_no_match_outside_a_pull_request(self):
        """github.head_ref is empty on push/schedule, so nothing matches."""
        self.assertFalse(is_advisory(True, "main", ""))

    def test_hotfix_prefix_is_not_a_substring_match(self):
        for head in ("not-a-hotfix/x", "feature-hotfix/x", "hotfixes/x", "hotfix"):
            with self.subTest(head=head):
                self.assertFalse(is_advisory(True, "main", head))


class DocumentationMatrixTests(unittest.TestCase):
    """Keeps the published matrix honest against the matching rule."""

    def setUp(self):
        section = DOCS.split("## Advisory lib version on hotfix PRs", 1)
        self.assertEqual(len(section), 2, "advisory section missing from docs")
        self.section = section[1].split("\n## ", 1)[0]

    def test_section_documents_input_and_default(self):
        self.assertIn(ADVISORY_INPUT, self.section)
        self.assertIn("**Matching rule.**", self.section)
        self.assertIn("`false` (default)", self.section)

    def test_production_example_uses_a_tier_channel(self):
        for line in self.section.splitlines():
            if "github-actions-shared-workflows/.github/workflows/" in line:
                self.assertRegex(line.strip(), r"@tier-[0-2]$")

    def test_documented_rows_agree_with_the_matching_rule(self):
        rows = 0
        for line in self.section.splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) != 4 or "→" not in cells[1] or "`" not in cells[1]:
                continue  # skips the header row, which also carries an arrow
            enabled_cell, branches, outdated_cell, verdict = cells
            head, base = (part.strip().strip("`") for part in branches.split("→"))
            if base == "any" or head == "any":
                continue

            enabled = enabled_cell.startswith("`true`")
            outdated = outdated_cell == "yes"
            should_fail = outdated and not is_advisory(enabled, base, head)

            with self.subTest(row=line.strip()):
                self.assertEqual(should_fail, "❌" in verdict, "documented verdict disagrees")
                self.assertEqual(not should_fail, "✅" in verdict, "documented verdict disagrees")
            rows += 1

        self.assertGreaterEqual(rows, 6, "expected the full branch matrix in the docs")


if __name__ == "__main__":
    unittest.main(verbosity=2)
