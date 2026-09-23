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

    def detect(self, payload, globs=DEFAULT_GLOBS, event="pull_request", before=None, after="head"):
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
                   "FIXTURE_JSON": str(fixture)}
            completed = subprocess.run(["bash", "-c", run_body("Detect non-doc changes")],
                                       env=env, capture_output=True, text=True, timeout=30)
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

    # ---- push events keep their own path ----

    def test_push_compare_diff_is_classified_by_path(self):
        payload = {"files": [{"filename": "internal/app.go"}]}
        self.assertEqual(self.detect(payload, event="push", before="a" * 40), "true")

    def test_push_without_base_ref_assumes_a_code_change(self):
        self.assertEqual(self.detect({"files": []}, event="push"), "true")


if __name__ == "__main__":
    unittest.main(verbosity=2)
