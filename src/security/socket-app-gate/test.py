#!/usr/bin/env python3
"""Run the shipped Bash steps with paginated gh fixtures, real jq, and no network.

Usage: python3 src/security/socket-app-gate/test.py
SOCKET_ACTION_PATH may point at a historical action.yml for a red/green replay.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import textwrap
import unittest

ACTION = Path(os.environ.get("SOCKET_ACTION_PATH", str(Path(__file__).with_name("action.yml"))))


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
assert "repos/example/service/commits/exact-head/check-runs?per_page=100" in args, args
state = pathlib.Path(os.environ["FIXTURE_STATE"])
count = int(state.read_text()) if state.exists() else 0
state.write_text(str(count + 1))
snapshots = json.loads(pathlib.Path(os.environ["FIXTURE_JSON"]).read_text())
snapshot = snapshots[min(count, len(snapshots) - 1)]
pages = snapshot["pages"]
if "--paginate" not in args:
    pages = pages[:1]
query = args[args.index("--jq") + 1] if "--jq" in args else None
assert not ("--slurp" in args and query), "gh rejects --slurp combined with --jq"
# gh --jq filters each response unless --slurp aggregates paginated responses.
values = [pages] if "--slurp" in args else pages
for value in values:
    if query is None:
        print(json.dumps(value))
        continue
    result = subprocess.run(["jq", "-c", query], input=json.dumps(value), text=True,
                            capture_output=True)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode:
        sys.exit(result.returncode)
# Simulate failure after an earlier page has already been emitted.
if snapshot.get("later_page_error") and "--paginate" in args:
    print("fixture: second-page API request failed", file=sys.stderr)
    sys.exit(1)
'''

FAKE_DATE = '''#!/usr/bin/env python3
import os, pathlib
state = pathlib.Path(os.environ["FIXTURE_CLOCK"])
now = int(state.read_text()) if state.exists() else 1000
state.write_text(str(now + 1))
print(now)
'''


def check(name, conclusion: str | None = "success", status="completed", app="socket-security"):
    return {"name": name, "status": status, "conclusion": conclusion,
            "app": {"slug": app}, "details_url": "https://socket.dev/dashboard/report",
            "output": {"title": "fixture", "summary": "fixture result"}}


def snapshot(*checks, later_page_error=False):
    unrelated = [check(f"other-{i}", app="github-actions") for i in range(100)]
    return {"pages": [{"check_runs": unrelated, "total_count": 100 + len(checks)},
                      {"check_runs": list(checks), "total_count": 100 + len(checks)}],
            "later_page_error": later_page_error}


class SocketAppGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for command in ("bash", "jq"):
            if not shutil.which(command):
                raise RuntimeError(f"required test command missing: {command}")

    def execute(self, snapshots, timeout=8):
        wait, evaluate, verdict, calls = self._execute(snapshots, timeout)
        self.assertEqual(wait.returncode, 0, wait.stdout + wait.stderr)
        assert evaluate is not None and verdict is not None
        return wait, evaluate, verdict, calls

    def _execute(self, snapshots, timeout=8):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binaries = root / "bin"
            binaries.mkdir()
            for name, content in (("gh", FAKE_GH), ("date", FAKE_DATE),
                                  ("sleep", "#!/bin/sh\nexit 0\n")):
                executable = binaries / name
                executable.write_text(textwrap.dedent(content))
                executable.chmod(0o700)
            fixture = root / "fixture.json"
            fixture.write_text(json.dumps(snapshots))
            output = root / "output"
            output.touch()
            env = {"PATH": str(binaries) + os.pathsep + os.environ["PATH"],
                   "RUNNER_TEMP": str(root), "GITHUB_OUTPUT": str(output),
                   "REPO": "example/service", "SHA": "exact-head",
                   "APP_SLUG": "socket-security", "TIMEOUT": str(timeout), "INTERVAL": "0",
                   "FIXTURE_JSON": str(fixture), "FIXTURE_STATE": str(root / "calls"),
                   "FIXTURE_CLOCK": str(root / "clock")}
            wait = subprocess.run(["bash", "-e", "-o", "pipefail", "-c",
                                   run_body("Wait for Socket App checks")], env=env,
                                  capture_output=True, text=True, timeout=10)
            values = dict(line.split("=", 1) for line in output.read_text().splitlines())
            calls = int((root / "calls").read_text())
            if wait.returncode:
                return wait, None, None, calls
            raw = json.loads(Path(values["raw_file"]).read_text())
            self.assertIsInstance(raw, list, "pages must become one result array")
            env.update(RAW_FILE=values["raw_file"], TIMED_OUT=values["timed_out"],
                       FAIL_ON_FINDINGS="true", ON_INCONCLUSIVE="block", ON_MISSING_APP="warn",
                       FINDINGS_FILE=str(root / "findings.json"))
            evaluate = subprocess.run(["bash", "-e", "-o", "pipefail", "-c",
                                       run_body("Evaluate Socket App verdict")], env=env,
                                      capture_output=True, text=True, timeout=10)
            verdict = json.loads((root / "findings.json").read_text())
            return wait, evaluate, verdict, calls

    def test_socket_checks_beyond_first_hundred(self):
        wait, evaluate, verdict, calls = self.execute([snapshot(check("Report"), check("Alerts"))])
        self.assertEqual(wait.returncode, 0, wait.stderr)
        self.assertEqual(evaluate.returncode, 0, evaluate.stdout + evaluate.stderr)
        self.assertEqual(verdict["verdict"], "pass")
        self.assertEqual([c["name"] for c in verdict["checks"]], ["Report", "Alerts"])
        self.assertEqual(calls, 2, "two identical complete snapshots are required")

    def test_single_page_keeps_existing_contract(self):
        _, evaluate, verdict, calls = self.execute([{"pages": [{"check_runs": [check("Report")]}]}])
        self.assertEqual(evaluate.returncode, 0)
        self.assertEqual(verdict["verdict"], "pass")
        self.assertEqual(calls, 2)

    def test_adverse_check_on_later_page_blocks(self):
        for conclusion in ("failure", "action_required", "cancelled", "timed_out"):
            with self.subTest(conclusion=conclusion):
                _, evaluate, verdict, _ = self.execute([snapshot(check("Report"), check("Alerts", conclusion))])
                self.assertNotEqual(evaluate.returncode, 0)
                self.assertEqual(verdict["verdict"], "findings")

    def test_neutral_or_skipped_on_later_page_blocks(self):
        for conclusion in ("neutral", "skipped"):
            with self.subTest(conclusion=conclusion):
                _, evaluate, verdict, _ = self.execute([snapshot(check("Report", conclusion))])
                self.assertNotEqual(evaluate.returncode, 0)
                self.assertEqual(verdict["verdict"], "inconclusive")

    def test_late_published_adverse_check_is_not_missed(self):
        first = snapshot(check("Report"))
        second = snapshot(check("Report"), check("Alerts", "failure"))
        _, evaluate, verdict, calls = self.execute([first, second])
        self.assertNotEqual(evaluate.returncode, 0)
        self.assertEqual(verdict["verdict"], "findings")
        self.assertEqual(calls, 3)

    def test_pending_later_page_waits_then_completes(self):
        pending = snapshot(check("Report", None, "in_progress"))
        _, evaluate, verdict, calls = self.execute([pending, snapshot(check("Report"))])
        self.assertEqual(evaluate.returncode, 0)
        self.assertEqual(verdict["verdict"], "pass")
        self.assertEqual(calls, 3)

    def test_partial_page_api_error_never_produces_verdict(self):
        wait, evaluate, verdict, _ = self._execute([snapshot(check("Report"), later_page_error=True)])
        self.assertNotEqual(wait.returncode, 0)
        self.assertIn("Could not read check runs", wait.stdout)
        self.assertIsNone(evaluate)
        self.assertIsNone(verdict)

    def test_no_checks_times_out_instead_of_passing(self):
        _, evaluate, verdict, _ = self.execute([snapshot()], timeout=2)
        self.assertNotEqual(evaluate.returncode, 0)
        self.assertEqual(verdict["verdict"], "inconclusive")
        self.assertTrue(verdict["timedOut"])

    def test_third_page_is_included_and_unrelated_failures_are_ignored(self):
        data = snapshot(check("Report"))
        data["pages"][0]["check_runs"][0]["conclusion"] = "failure"
        data["pages"].append({"check_runs": [check("Alerts", "failure")]})
        _, evaluate, verdict, _ = self.execute([data])
        self.assertNotEqual(evaluate.returncode, 0)
        self.assertEqual(verdict["verdict"], "findings")
        self.assertEqual(len(verdict["checks"]), 2)


if __name__ == "__main__":
    unittest.main()
