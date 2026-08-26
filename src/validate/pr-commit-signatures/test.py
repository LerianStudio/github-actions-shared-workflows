#!/usr/bin/env python3
"""Behavioural tests for the pr-commit-signatures composite action.

Same extract/execute/parse shape as
src/validate/permission-manifest-publish/test.py, adapted to a `github-script`
step: the embedded `script: |` body is pulled out of action.yml by step name and
executed by a JS runtime inside an async wrapper that stubs `core`, `github`, and
`context`. The stubbed `github.paginate` walks pages exactly like Octokit does,
so pagination is exercised for real instead of being mocked away.

The wrapper prints a single JSON blob on stdout; every assertion reads it.
"""

import json
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ACTION_PATH = Path(__file__).resolve().parent / "action.yml"
ACTION = ACTION_PATH.read_text(encoding="utf-8")

STEP_NAME = "Verify commit signatures"

# node in CI; bun is accepted so the suite is runnable on workstations without node.
RUNTIME = shutil.which("node") or shutil.which("bun")


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


def extract_script_body(text, step_name):
    step = extract_step(text, step_name)
    lines = step.splitlines()
    for start, line in enumerate(lines):
        if line.strip() == "script: |":
            script_indent = indentation(line)
            break
    else:
        raise AssertionError(f"script body not found for step: {step_name}")

    body = []
    for line in lines[start + 1:]:
        if line.strip() and indentation(line) <= script_indent:
            break
        body.append(line)
    return textwrap.dedent("\n".join(body)).rstrip() + "\n"


SCRIPT_BODY = extract_script_body(ACTION, STEP_NAME)

HARNESS = """
const FIXTURE = __FIXTURE__;
const DECLARED = __DECLARED__;
const DRY_RUN = __DRY_RUN__;
const HAS_PR = __HAS_PR__;

process.env.DRY_RUN = DRY_RUN;

const record = {
  failed: false,
  failedMessage: null,
  outputs: {},
  summary: '',
  errors: [],
  notices: [],
  infos: [],
  listCommitsCalls: [],
};

const core = {
  setFailed: (m) => { record.failed = true; record.failedMessage = String(m); },
  setOutput: (k, v) => { record.outputs[k] = String(v); },
  error: (m) => record.errors.push(String(m)),
  notice: (m) => record.notices.push(String(m)),
  warning: (m) => record.infos.push(String(m)),
  info: (m) => record.infos.push(String(m)),
  summary: {
    addRaw(text) { record.summary += String(text); return this; },
    async write() { return this; },
  },
};

const context = {
  repo: { owner: 'LerianStudio', repo: 'example' },
  serverUrl: 'https://github.com',
  runId: 42,
  issue: { number: 7 },
  payload: HAS_PR
    ? { pull_request: { number: 7, commits: DECLARED, base: { ref: 'main' } } }
    : {},
};

// Mirrors the Octokit endpoint: slices the fixture by page/per_page. The API caps
// the endpoint at 250 commits, so anything beyond that is never returned.
const listCommits = async (params) => {
  record.listCommitsCalls.push({ page: params.page ?? 1, per_page: params.per_page });
  const perPage = params.per_page ?? 30;
  const page = params.page ?? 1;
  const capped = FIXTURE.slice(0, 250);
  const start = (page - 1) * perPage;
  return { data: capped.slice(start, start + perPage) };
};

const github = {
  rest: { pulls: { listCommits } },
  // Octokit's paginate: keeps requesting pages until one comes back short.
  paginate: async (endpoint, params) => {
    const perPage = params.per_page ?? 30;
    const all = [];
    for (let page = 1; ; page += 1) {
      const { data } = await endpoint({ ...params, page });
      all.push(...data);
      if (data.length < perPage) break;
    }
    return all;
  },
};

(async () => {
__SCRIPT__
})()
  .catch((err) => { record.failed = true; record.failedMessage = `threw: ${err && err.message}`; })
  .then(() => { process.stdout.write(JSON.stringify(record)); });
"""


def commit(index, verified, reason="valid", login="dev"):
    sha = f"{index:040x}"
    return {
        "sha": sha,
        "html_url": f"https://github.com/LerianStudio/example/commit/{sha}",
        "author": {"login": login} if login else None,
        "commit": {
            "author": {"name": "Dev Name"},
            "verification": {"verified": verified, "reason": reason},
        },
    }


def run_script(commits, declared=None, dry_run="false", has_pr=True):
    if RUNTIME is None:
        raise unittest.SkipTest("no JS runtime (node/bun) available")

    harness = (
        HARNESS.replace("__FIXTURE__", json.dumps(commits))
        .replace("__DECLARED__", json.dumps(len(commits) if declared is None else declared))
        .replace("__DRY_RUN__", json.dumps(dry_run))
        .replace("__HAS_PR__", "true" if has_pr else "false")
        .replace("__SCRIPT__", textwrap.indent(SCRIPT_BODY, "  "))
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        script_path = Path(temp_dir) / "harness.mjs"
        script_path.write_text(harness, encoding="utf-8")
        result = subprocess.run(
            [RUNTIME, str(script_path)],
            text=True,
            capture_output=True,
            check=False,
        )

    if result.returncode != 0:
        raise AssertionError(
            f"harness exited {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return json.loads(result.stdout)


@unittest.skipIf(RUNTIME is None, "no JS runtime (node/bun) available")
class CommitSignatureValidation(unittest.TestCase):
    # (a) Every commit verified -> success, no offenders reported.
    def test_all_verified_passes(self):
        record = run_script([commit(i, True) for i in range(1, 6)])
        self.assertFalse(record["failed"], msg=record["failedMessage"])
        self.assertEqual(record["outputs"]["total-commits"], "5")
        self.assertEqual(record["outputs"]["unverified-count"], "0")
        self.assertEqual(record["outputs"]["has-signature-failures"], "false")
        self.assertEqual(record["errors"], [])
        self.assertIn("verified signature", record["summary"])

    # (b) Mixed set -> failure, and EVERY offender is reported, not just the first.
    def test_mixed_set_reports_every_offender(self):
        commits = [
            commit(1, True),
            commit(2, False, "unsigned", login="alice"),
            commit(3, True),
            commit(4, False, "unknown_key", login="bob"),
        ]
        record = run_script(commits)
        self.assertTrue(record["failed"])
        self.assertEqual(record["outputs"]["unverified-count"], "2")
        self.assertEqual(record["outputs"]["has-signature-failures"], "true")
        self.assertEqual(len(record["errors"]), 2)
        joined = "\n".join(record["errors"])
        self.assertIn("unsigned", joined)
        self.assertIn("unknown_key", joined)
        self.assertIn("alice", joined)
        self.assertIn("bob", joined)
        # Both offenders present in the summary table, with short SHA + link.
        self.assertIn(f"[`{2:040x}"[:8], record["summary"])
        self.assertIn(f"[`{4:040x}"[:8], record["summary"])
        self.assertIn("How to fix", record["summary"])
        self.assertIn("2 of 4 commit(s)", record["failedMessage"])

    # (c) A missing verification block is treated as unverified, not as a pass.
    def test_missing_verification_block_is_unverified(self):
        broken = commit(1, True)
        del broken["commit"]["verification"]
        record = run_script([broken])
        self.assertTrue(record["failed"])
        self.assertEqual(record["outputs"]["unverified-count"], "1")
        self.assertIn("unknown", record["errors"][0])

    # (d) >100 commits: paginate must walk every page, per_page must be 100.
    def test_paginated_set_is_fully_evaluated(self):
        commits = [commit(i, True) for i in range(1, 250)]
        commits[240] = commit(241, False, "unsigned")
        record = run_script(commits)
        self.assertTrue(record["failed"])
        self.assertEqual(record["outputs"]["total-commits"], "249")
        self.assertEqual(record["outputs"]["unverified-count"], "1")
        self.assertEqual(
            [call["page"] for call in record["listCommitsCalls"]], [1, 2, 3]
        )
        self.assertTrue(all(c["per_page"] == 100 for c in record["listCommitsCalls"]))

    # (e) 200 verified commits across two pages -> still a pass.
    def test_paginated_all_verified_passes(self):
        record = run_script([commit(i, True) for i in range(1, 201)])
        self.assertFalse(record["failed"], msg=record["failedMessage"])
        self.assertEqual(record["outputs"]["total-commits"], "200")
        self.assertEqual(record["outputs"]["unverified-count"], "0")
        self.assertEqual(record["outputs"]["has-signature-failures"], "false")

    # (f) Beyond the 250-commit API cap the verdict cannot be complete -> fail closed.
    def test_beyond_api_cap_fails_closed(self):
        record = run_script([commit(i, True) for i in range(1, 320)], declared=319)
        self.assertTrue(record["failed"])
        self.assertEqual(record["outputs"]["total-commits"], "250")
        # Every returned commit is verified, so the count alone would read as a pass;
        # has-signature-failures is what tells a caller the verdict is incomplete.
        self.assertEqual(record["outputs"]["unverified-count"], "0")
        self.assertEqual(record["outputs"]["has-signature-failures"], "true")
        self.assertIn("could not evaluate all 319", record["failedMessage"])
        self.assertIn("250 commits", record["summary"])

    # (g) dry-run reports findings but never fails the check.
    def test_dry_run_does_not_fail(self):
        record = run_script(
            [commit(1, True), commit(2, False, "unsigned")], dry_run="true"
        )
        self.assertFalse(record["failed"], msg=record["failedMessage"])
        self.assertEqual(record["outputs"]["unverified-count"], "1")
        self.assertEqual(len(record["errors"]), 1)
        self.assertEqual(len(record["notices"]), 1)
        self.assertIn("DRY RUN", record["notices"][0])
        self.assertIn("DRY RUN", record["summary"])

    # (h) Non-pull_request payload fails instead of silently passing.
    def test_missing_pull_request_payload_fails(self):
        record = run_script([commit(1, True)], has_pr=False)
        self.assertTrue(record["failed"])
        self.assertIn("pull_request", record["failedMessage"])


if __name__ == "__main__":
    unittest.main()
