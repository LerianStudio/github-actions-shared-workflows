#!/usr/bin/env python3
"""Behavioural tests for the coderabbit-collapse composite action.

Same extract/execute/parse shape as src/validate/pr-commit-signatures/test.py: the
embedded `script: |` body is pulled out of action.yml by step name and executed by a JS
runtime inside an async wrapper that stubs `core`, `github`, and `context`.

The stubbed `github.graphql` serves the two paginated connections the script reads and
records every mutation it attempts, so the review -> threads grouping and the fold /
restore decisions are exercised for real rather than mocked away.

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

STEP_NAME = "Collapse resolved reviews"

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
const REVIEWS = __REVIEWS__;
const THREADS = __THREADS__;
const PR_NUMBER = __PR_NUMBER__;
const AUTHORS = __AUTHORS__;
const DRY_RUN = __DRY_RUN__;
const MUTATIONS_FAIL = __MUTATIONS_FAIL__;

process.env.PR_NUMBER = PR_NUMBER;
process.env.AUTHORS = AUTHORS;
process.env.DRY_RUN = DRY_RUN;

const record = {
  failed: false,
  failedMessage: null,
  outputs: {},
  summary: '',
  infos: [],
  warnings: [],
  mutations: [],
  pages: { reviews: 0, reviewThreads: 0 },
};

const core = {
  setFailed: (m) => { record.failed = true; record.failedMessage = String(m); },
  setOutput: (k, v) => { record.outputs[k] = String(v); },
  error: (m) => record.warnings.push(String(m)),
  notice: (m) => record.infos.push(String(m)),
  warning: (m) => record.warnings.push(String(m)),
  info: (m) => record.infos.push(String(m)),
  summary: {
    addRaw(text) { record.summary += String(text); return this; },
    async write() { return this; },
  },
};

const context = { repo: { owner: 'LerianStudio', repo: 'example' } };

// Mirrors a GraphQL connection: 100 nodes a page, the cursor being the offset.
const page = (nodes, cursor) => {
  const start = cursor ? Number(cursor) : 0;
  const slice = nodes.slice(start, start + 100);
  const next = start + 100;
  return {
    pageInfo: { hasNextPage: next < nodes.length, endCursor: String(next) },
    nodes: slice,
  };
};

const graphql = async (query, variables) => {
  // `unminimizeComment` contains `minimizeComment` as a substring, so it is tested first.
  if (query.includes('unminimizeComment(')) {
    if (MUTATIONS_FAIL) throw new Error('stubbed mutation failure');
    record.mutations.push({ op: 'unminimize', id: variables.id });
    return { unminimizeComment: { unminimizedComment: { isMinimized: false } } };
  }
  if (query.includes('minimizeComment(')) {
    if (MUTATIONS_FAIL) throw new Error('stubbed mutation failure');
    record.mutations.push({
      op: 'minimize',
      id: variables.id,
      // The classifier is what makes the fold reversible by this same action later.
      classifier: (query.match(/classifier:\\s*([A-Z_]+)/) || [])[1],
    });
    return { minimizeComment: { minimizedComment: { isMinimized: true } } };
  }

  const field = query.includes('reviewThreads(') ? 'reviewThreads' : 'reviews';
  record.pages[field] += 1;
  const nodes = field === 'reviewThreads' ? THREADS : REVIEWS;
  return {
    repository: { pullRequest: { [field]: page(nodes, variables.cursor) } },
  };
};

const github = { graphql };

(async () => {
__SCRIPT__
})()
  .catch((err) => { record.failed = true; record.failedMessage = `threw: ${err && err.message}`; })
  .then(() => { process.stdout.write(JSON.stringify(record)); });
"""


def review(index, login="coderabbitai", body="Actionable comments posted: 2",
           minimized=False, reason=None):
    return {
        "id": f"PRR_{index:08d}",
        "author": {"login": login},
        "isMinimized": minimized,
        "minimizedReason": reason,
        "body": body,
    }


def thread(review_index, resolved, orphan=False):
    """A review thread, as GraphQL returns it: the opening comment names the parent."""
    parent = None if orphan else {"id": f"PRR_{review_index:08d}"}
    return {
        "isResolved": resolved,
        "comments": {"nodes": [{"pullRequestReview": parent}]},
    }


def run_script(reviews, threads, pr_number="7", authors="coderabbitai[bot]",
               dry_run="false", mutations_fail=False):
    if RUNTIME is None:
        raise unittest.SkipTest("no JS runtime (node/bun) available")

    harness = (
        HARNESS.replace("__REVIEWS__", json.dumps(reviews))
        .replace("__THREADS__", json.dumps(threads))
        .replace("__PR_NUMBER__", json.dumps(pr_number))
        .replace("__AUTHORS__", json.dumps(authors))
        .replace("__DRY_RUN__", json.dumps(dry_run))
        .replace("__MUTATIONS_FAIL__", "true" if mutations_fail else "false")
        .replace("__SCRIPT__", textwrap.indent(SCRIPT_BODY, "  "))
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        script_path = Path(temp_dir) / "harness.cjs"
        script_path.write_text(harness, encoding="utf-8")
        try:
            # Without a deadline, a regression that never settles a promise leaves the
            # suite hanging until the runner's own timeout, with nothing to read.
            result = subprocess.run(
                [RUNTIME, str(script_path)],
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
        except subprocess.TimeoutExpired as expired:
            raise AssertionError(
                f"harness did not finish within {expired.timeout}s "
                f"(reviews={len(reviews)}, threads={len(threads)}, dry_run={dry_run})\n"
                f"stdout:\n{expired.stdout}\nstderr:\n{expired.stderr}"
            ) from expired

    if result.returncode != 0:
        raise AssertionError(
            f"harness exited {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return json.loads(result.stdout)


@unittest.skipIf(RUNTIME is None, "no JS runtime (node/bun) available")
class CollapseResolvedReviews(unittest.TestCase):
    # (a) The whole point: every thread a review opened is resolved -> fold the summary.
    def test_all_threads_resolved_folds_the_review(self):
        record = run_script([review(1)], [thread(1, True), thread(1, True)])
        self.assertFalse(record["failed"], msg=record["failedMessage"])
        self.assertEqual(record["outputs"]["evaluated"], "1")
        self.assertEqual(record["outputs"]["collapsed"], "1")
        self.assertEqual(record["outputs"]["restored"], "0")
        self.assertEqual(len(record["mutations"]), 1)
        self.assertEqual(record["mutations"][0]["op"], "minimize")
        self.assertEqual(record["mutations"][0]["id"], "PRR_00000001")
        # RESOLVED is what lets this same action recognise and undo its own fold later.
        self.assertEqual(record["mutations"][0]["classifier"], "RESOLVED")
        self.assertIn("folded", record["summary"])

    # (b) One unresolved child is enough to keep the summary visible.
    def test_one_unresolved_thread_keeps_the_review_open(self):
        record = run_script([review(1)], [thread(1, True), thread(1, False)])
        self.assertEqual(record["outputs"]["collapsed"], "0")
        self.assertEqual(record["mutations"], [])
        self.assertIn("left open", record["summary"])

    # (c) Idempotent: a fold already in place is not reapplied on every thread event.
    def test_already_minimized_review_is_not_refolded(self):
        record = run_script(
            [review(1, minimized=True, reason="resolved")], [thread(1, True)]
        )
        self.assertEqual(record["outputs"]["collapsed"], "0")
        self.assertEqual(record["mutations"], [])
        self.assertIn("already folded", record["summary"])

    # (d) A review with no inline thread is never folded. This is the gate's warning
    # honoured: a summary and its findings are the same object, so folding on a
    # condition nobody can satisfy would hide findings for good.
    def test_review_without_threads_is_left_alone(self):
        record = run_script([review(1)], [])
        self.assertEqual(record["outputs"]["evaluated"], "0")
        self.assertEqual(record["mutations"], [])
        self.assertIn("No eligible review", "\n".join(record["infos"]))

    # (e) A thread whose opening comment names no review cannot make its review foldable.
    def test_orphan_thread_does_not_make_a_review_foldable(self):
        record = run_script([review(1)], [thread(1, True, orphan=True)])
        self.assertEqual(record["outputs"]["evaluated"], "0")
        self.assertEqual(record["mutations"], [])

    # (f) Human reviews are out of scope — only the configured authors are touched.
    def test_other_authors_are_ignored(self):
        record = run_script(
            [review(1, login="bedatty"), review(2)],
            [thread(1, True), thread(2, True)],
        )
        self.assertEqual(record["outputs"]["evaluated"], "1")
        self.assertEqual([m["id"] for m in record["mutations"]], ["PRR_00000002"])

    # (g) Every reply posts a review of its own with no body; nothing renders, so there is
    # nothing to fold.
    def test_bodyless_reply_reviews_are_ignored(self):
        record = run_script(
            [review(1, body=""), review(2, body="   ")], [thread(1, True), thread(2, True)]
        )
        self.assertEqual(record["outputs"]["evaluated"], "0")
        self.assertEqual(record["mutations"], [])

    # (h) Reopening a thread makes the summary relevant again -> restore it.
    def test_reopened_thread_restores_a_folded_review(self):
        record = run_script(
            [review(1, minimized=True, reason="resolved")],
            [thread(1, True), thread(1, False)],
        )
        self.assertEqual(record["outputs"]["restored"], "1")
        self.assertEqual(record["outputs"]["collapsed"], "0")
        self.assertEqual(len(record["mutations"]), 1)
        self.assertEqual(record["mutations"][0]["op"], "unminimize")
        self.assertIn("restored", record["summary"])

    # (i) Only this action's own fold is undone. Something hidden as spam or off-topic was
    # hidden for a reason that has nothing to do with threads.
    def test_reviews_hidden_for_other_reasons_are_not_restored(self):
        for reason in ("spam", "off_topic", "outdated", "duplicate", None):
            with self.subTest(reason=reason):
                record = run_script(
                    [review(1, minimized=True, reason=reason)], [thread(1, False)]
                )
                self.assertEqual(record["mutations"], [])
                self.assertEqual(record["outputs"]["restored"], "0")

    # (j) dry-run reports the decision and mutates nothing. `collapsed` counts mutations
    # that happened, so a caller reading it as a state change must not be misled by a run
    # that changed nothing — the plan belongs in the summary, not in the counter.
    def test_dry_run_reports_without_mutating(self):
        record = run_script([review(1)], [thread(1, True)], dry_run="true")
        self.assertEqual(record["mutations"], [])
        self.assertEqual(record["outputs"]["collapsed"], "0")
        self.assertEqual(record["outputs"]["has-changes"], "false")
        self.assertEqual(record["outputs"]["evaluated"], "1")
        self.assertIn("DRY RUN", record["summary"])
        self.assertIn("would fold: **1**", record["summary"])

    def test_dry_run_reports_a_restore_without_mutating(self):
        record = run_script(
            [review(1, minimized=True, reason="resolved")],
            [thread(1, False)],
            dry_run="true",
        )
        self.assertEqual(record["mutations"], [])
        self.assertEqual(record["outputs"]["restored"], "0")
        self.assertEqual(record["outputs"]["has-changes"], "false")
        self.assertIn("would restore: **1**", record["summary"])

    # (j2) has-changes is the boolean a caller gates downstream work on, and it tracks
    # mutations that actually landed — not ones that were merely planned or attempted.
    def test_has_changes_tracks_real_mutations(self):
        folded = run_script([review(1)], [thread(1, True)])
        self.assertEqual(folded["outputs"]["has-changes"], "true")

        restored = run_script(
            [review(1, minimized=True, reason="resolved")], [thread(1, False)]
        )
        self.assertEqual(restored["outputs"]["has-changes"], "true")

        for name, record in (
            ("nothing to do", run_script([review(1)], [thread(1, False)])),
            ("no eligible review", run_script([review(1)], [])),
            ("mutation failed", run_script([review(1)], [thread(1, True)], mutations_fail=True)),
        ):
            with self.subTest(case=name):
                self.assertEqual(record["outputs"]["has-changes"], "false")

    # (k) REST says `coderabbitai[bot]`, GraphQL says `coderabbitai`. Callers copy
    # whichever they last saw, so both spellings must match the same bot.
    def test_author_matching_ignores_the_bot_suffix(self):
        for configured in ("coderabbitai[bot]", "coderabbitai", " CodeRabbitAI ",
                           "someone-else,coderabbitai"):
            with self.subTest(authors=configured):
                record = run_script([review(1)], [thread(1, True)], authors=configured)
                self.assertEqual(record["outputs"]["collapsed"], "1", msg=configured)

    # (l) An empty author list is a no-op, not a pass that folds everything.
    def test_empty_author_list_does_nothing(self):
        record = run_script([review(1)], [thread(1, True)], authors="  ,  ")
        self.assertEqual(record["mutations"], [])
        self.assertEqual(record["outputs"]["evaluated"], "0")

    # (m) Both connections are paginated, so a long-running pull request is fully read.
    def test_both_connections_are_paginated(self):
        reviews = [review(i) for i in range(1, 151)]
        threads = [thread(i, True) for i in range(1, 151)] + [thread(1, True)] * 100
        record = run_script(reviews, threads)
        self.assertEqual(record["outputs"]["evaluated"], "150")
        self.assertEqual(record["outputs"]["collapsed"], "150")
        self.assertEqual(record["pages"]["reviews"], 2)
        self.assertEqual(record["pages"]["reviewThreads"], 3)

    # (n) Tidying is never worth a red check: the review itself is the product.
    def test_mutation_failure_warns_instead_of_failing(self):
        record = run_script([review(1)], [thread(1, True)], mutations_fail=True)
        self.assertFalse(record["failed"], msg=record["failedMessage"])
        self.assertEqual(record["outputs"]["collapsed"], "0")
        self.assertEqual(len(record["warnings"]), 1)
        self.assertIn("Could not fold", record["warnings"][0])
        self.assertIn("fold failed", record["summary"])

    # (o) A pr-number that is not a positive integer is a configuration error, not
    # something to guess at.
    def test_invalid_pr_number_fails(self):
        for value in ("", "abc", "0", "-3", "7.5"):
            with self.subTest(pr_number=value):
                record = run_script([review(1)], [thread(1, True)], pr_number=value)
                self.assertTrue(record["failed"], msg=value)
                self.assertIn("pr-number", record["failedMessage"])
                self.assertEqual(record["mutations"], [])


if __name__ == "__main__":
    unittest.main()
