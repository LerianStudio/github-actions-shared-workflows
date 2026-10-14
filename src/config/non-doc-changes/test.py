#!/usr/bin/env python3
"""Run the shipped Bash step against gh fixtures, real jq, and no network.

Usage: python3 src/config/non-doc-changes/test.py
NON_DOC_ACTION_PATH may point at a historical action.yml for a red/green replay.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ACTION = Path(os.environ.get("NON_DOC_ACTION_PATH", str(Path(__file__).with_name("action.yml"))))

DEFAULT_GLOBS = "*.md docs/* .github/* LICENSE* .gitignore .coderabbit.yml .coderabbit.yaml"


def run_body(name):
    lines = ACTION.read_text().splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == f"- name: {name}")
    start = next(i for i in range(start + 1, len(lines)) if lines[i].strip() == "run: |")
    body = []
    for line in lines[start + 1:]:
        if line.strip() and not line.startswith("        "):
            break
        body.append(line[8:])
    return "\n".join(body)


FAKE_GH = '''#!/usr/bin/env python3
import json, os, pathlib, subprocess, sys
args = sys.argv[1:]
assert args[0] == "api", args
payload = json.loads(pathlib.Path(os.environ["FIXTURE_JSON"]).read_text())
query = args[args.index("--jq") + 1] if "--jq" in args else None
if query is None:
    print(json.dumps(payload))
    sys.exit(0)
result = subprocess.run(["jq", "-r", query], input=json.dumps(payload), text=True,
                        capture_output=True)
sys.stdout.write(result.stdout)
sys.stderr.write(result.stderr)
sys.exit(result.returncode)
'''


def pr_files(*entries):
    """GitHub's pulls/{n}/files shape: (filename, status) pairs."""
    return [{"filename": name, "status": status} for name, status in entries]


class NonDocChangesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for command in ("bash", "jq"):
            if not shutil.which(command):
                raise RuntimeError(f"required test command missing: {command}")

    def detect(self, payload, globs=DEFAULT_GLOBS, event="pull_request", before=None, after="head",
               workflow_paths_are_code="true", expect_failure=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binaries = root / "bin"
            binaries.mkdir()
            gh = binaries / "gh"
            gh.write_text(FAKE_GH)
            gh.chmod(0o700)
            fixture = root / "fixture.json"
            fixture.write_text(json.dumps(payload))
            output = root / "output"
            output.touch()
            env = {"PATH": str(binaries) + os.pathsep + os.environ["PATH"],
                   "GITHUB_OUTPUT": str(output), "GH_TOKEN": "fixture-token",
                   "IGNORE_GLOBS": globs, "EVENT_NAME": event,
                   "REPO": "example/service", "PR_NUMBER": "42",
                   "BEFORE": before or "0" * 40, "AFTER": after,
                   "WORKFLOW_PATHS_ARE_CODE": workflow_paths_are_code,
                   "FIXTURE_JSON": str(fixture)}
            completed = subprocess.run(["bash", "-c", run_body("Detect non-doc changes")],
                                       env=env, capture_output=True, text=True, timeout=30)
            if expect_failure:
                self.assertNotEqual(completed.returncode, 0, completed.stdout + completed.stderr)
                return completed.stdout + completed.stderr
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            values = dict(line.split("=", 1) for line in output.read_text().splitlines())
            return values["code"]

    # ---- the defect: a pull request made only of deletions ----

    def test_deletion_only_go_file_is_a_code_change(self):
        self.assertEqual(self.detect(pr_files(("internal/ledger/entry.go", "removed"))), "true")

    def test_deletion_only_markdown_file_is_not_a_code_change(self):
        self.assertEqual(self.detect(pr_files(("docs/guide.md", "removed"))), "false")

    def test_deletion_only_mixed_diff_counts_the_code_file(self):
        self.assertEqual(self.detect(pr_files(("README.md", "removed"),
                                              ("main.go", "removed"))), "true")

    # ---- the rules that must not change ----

    def test_added_go_file_is_a_code_change(self):
        self.assertEqual(self.detect(pr_files(("cmd/app/main.go", "added"))), "true")

    def test_modified_markdown_only_is_not_a_code_change(self):
        self.assertEqual(self.detect(pr_files(("README.md", "modified"),
                                              ("docs/setup.md", "modified"))), "false")

    def test_renamed_code_file_is_a_code_change(self):
        self.assertEqual(self.detect(pr_files(("pkg/util/clock.go", "renamed"))), "true")

    def test_empty_diff_is_not_a_code_change(self):
        self.assertEqual(self.detect([]), "false")

    def test_ignore_globs_input_is_honoured(self):
        self.assertEqual(self.detect(pr_files(("build/out.txt", "removed")),
                                     globs="build/*"), "false")

    # ---- executable paths under .github are never documentation ----
    #
    # In a bash `case` pattern `*` matches `/`, so the default `.github/*` glob
    # swallows every nested path. Only the hardcoded exceptions keep composite
    # actions and pipeline helper scripts out of the documentation bucket.

    def test_workflow_file_is_a_code_change(self):
        self.assertEqual(self.detect(pr_files((".github/workflows/build.yml", "modified"))), "true")

    def test_composite_action_is_a_code_change(self):
        self.assertEqual(self.detect(pr_files((".github/actions/setup/action.yml", "modified"))), "true")

    def test_pipeline_script_is_a_code_change(self):
        self.assertEqual(self.detect(pr_files((".github/scripts/release.sh", "modified"))), "true")

    def test_github_metadata_is_still_documentation(self):
        self.assertEqual(self.detect(pr_files((".github/CODEOWNERS", "modified"),
                                              (".github/dependabot.yml", "modified"),
                                              (".github/ISSUE_TEMPLATE/bug.yml", "modified"))), "false")

    # ---- workflow-paths-are-code=false: the release caller's reading ----
    #
    # A push that touches only the pipeline definition ships byte-identical
    # code. Releasing it moves GitOps tags in every environment following the
    # branch and writes a changelog entry for an internal CI tweak, so release
    # callers turn the exception off and let `.github/*` do its job.

    def test_workflow_file_is_documentation_when_the_exception_is_off(self):
        self.assertEqual(self.detect(pr_files((".github/workflows/release.yml", "modified")),
                                     workflow_paths_are_code="false"), "false")

    def test_composite_action_is_documentation_when_the_exception_is_off(self):
        self.assertEqual(self.detect(pr_files((".github/actions/setup/action.yml", "modified")),
                                     workflow_paths_are_code="false"), "false")

    def test_pipeline_script_is_documentation_when_the_exception_is_off(self):
        self.assertEqual(self.detect(pr_files((".github/scripts/release.sh", "modified")),
                                     workflow_paths_are_code="false"), "false")

    def test_workflow_change_alongside_code_still_releases(self):
        self.assertEqual(self.detect(pr_files((".github/workflows/release.yml", "modified"),
                                              ("internal/ledger/entry.go", "modified")),
                                     workflow_paths_are_code="false"), "true")

    def test_exception_off_still_honours_a_glob_set_that_omits_dot_github(self):
        """Turning the exception off defers to the globs; it does not force docs."""
        self.assertEqual(self.detect(pr_files((".github/workflows/release.yml", "modified")),
                                     globs="*.md docs/*", workflow_paths_are_code="false"), "true")

    # ---- the flag decides; it never guesses ----

    def test_unrecognised_flag_value_fails_the_step(self):
        output = self.detect(pr_files(("main.go", "modified")),
                             workflow_paths_are_code="yes", expect_failure=True)
        self.assertIn("workflow-paths-are-code", output)

    def test_empty_flag_value_fails_the_step(self):
        self.detect(pr_files(("main.go", "modified")),
                    workflow_paths_are_code="", expect_failure=True)

    # ---- push events keep their own path ----

    def test_push_compare_diff_is_classified_by_path(self):
        payload = {"files": [{"filename": "internal/app.go"}]}
        self.assertEqual(self.detect(payload, event="push", before="a" * 40), "true")

    def test_push_without_base_ref_assumes_a_code_change(self):
        self.assertEqual(self.detect({"files": []}, event="push"), "true")

    # ---- a truncated compare is not a verdict ----
    #
    # The compare endpoint caps `files` at 300 and signals the cap only by
    # hitting it. A push whose first 300 entries are documentation must not be
    # read as documentation-only just because the code was cut off the list.

    def test_push_at_the_compare_ceiling_assumes_a_code_change(self):
        payload = {"files": [{"filename": f"docs/page-{i}.md"} for i in range(300)]}
        self.assertEqual(self.detect(payload, event="push", before="a" * 40), "true")

    def test_push_below_the_compare_ceiling_is_still_classified(self):
        payload = {"files": [{"filename": f"docs/page-{i}.md"} for i in range(299)]}
        self.assertEqual(self.detect(payload, event="push", before="a" * 40), "false")


if __name__ == "__main__":
    unittest.main(verbosity=2)
