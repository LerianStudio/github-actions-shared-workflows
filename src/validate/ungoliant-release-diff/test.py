#!/usr/bin/env python3

"""Behavioural tests for the ungoliant-release-diff composite.

The reference implementation is `docs/testing/cluster/test-release.sh` in the
ungoliant-controller repository. This suite pins the two things that had drifted
away from it:

  * the payload must NOT carry a target_env, because the controller honours one
    OVER the application's registration; and
  * `accepted` and `no_applicable_stages` are delivered releases, not failures.

Both layers run the composite's own extracted shell against fixtures, so they
test the shipped script rather than a restatement of it.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ACTION_PATH = REPO_ROOT / "src" / "validate" / "ungoliant-release-diff" / "action.yml"
GO_RELEASE_PATH = REPO_ROOT / ".github" / "workflows" / "go-release.yml"
JS_RELEASE_PATH = REPO_ROOT / ".github" / "workflows" / "js-release.yml"

ACTION = ACTION_PATH.read_text(encoding="utf-8")
GO_RELEASE = GO_RELEASE_PATH.read_text(encoding="utf-8")
JS_RELEASE = JS_RELEASE_PATH.read_text(encoding="utf-8")

PAYLOAD_STEP = "Build payload"
WEBHOOK_STEP = "Send release-diff webhook"


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


PAYLOAD_SCRIPT = extract_run_body(ACTION, PAYLOAD_STEP)
WEBHOOK_SCRIPT = extract_run_body(ACTION, WEBHOOK_STEP)

# The webhook step's only outbound call. Replacing curl with a stub that prints a
# canned body lets the real verdict logic run against every documented status.
CURL_STUB = """
curl() {
  printf '%s' "$STUB_RESPONSE"
}
export -f curl 2>/dev/null || true
"""


class ScriptRunner:
    def __init__(self, testcase):
        self.dir = Path(tempfile.mkdtemp(prefix="ungoliant-release-diff-"))
        testcase.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def run(self, script, prelude="", **env_overrides):
        outputs = self.dir / "github_output"
        summary = self.dir / "github_step_summary"
        outputs.write_text("", encoding="utf-8")
        summary.write_text("", encoding="utf-8")

        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(self.dir),
            "GITHUB_OUTPUT": str(outputs),
            "GITHUB_STEP_SUMMARY": str(summary),
            "RUNNER_TEMP": str(self.dir),
        }
        env.update({k: str(v) for k, v in env_overrides.items()})

        result = subprocess.run(
            [BASH, "-c", prelude + "\n" + script],
            cwd=self.dir, env=env, capture_output=True, text=True,
        )
        result.github_output = outputs.read_text(encoding="utf-8")
        result.step_summary = summary.read_text(encoding="utf-8")
        result.outputs = dict(
            line.split("=", 1) for line in result.github_output.splitlines() if "=" in line
        )
        return result


PAYLOAD_ENV = {
    "APP": "midaz",
    "ENV": "beta",
    "REPO": "LerianStudio/midaz",
    "VERSION": "v4.1.0-beta.2",
    "REVISION": "abc123def456",
    "PREV_SHA": "111222333444",
    "TARGET_ENV": "chaos-dev-st",
}


@unittest.skipUnless(BASH, "requires bash 4+")
class PayloadTests(unittest.TestCase):
    """The registration decides where a release is validated — not this argument."""

    def setUp(self):
        self.runner = ScriptRunner(self)
        (self.runner.dir / "diff.txt").write_text("--- a/x\n+++ b/x\n", encoding="utf-8")

    def _payload(self, send_target_env):
        result = self.runner.run(
            PAYLOAD_SCRIPT, SEND_TARGET_ENV=send_target_env, **PAYLOAD_ENV
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads((self.runner.dir / "payload.json").read_text(encoding="utf-8")), result

    def test_target_env_is_not_sent_by_default(self):
        payload, _ = self._payload("false")
        self.assertNotIn("target_env", payload)

    def test_payload_carries_the_release_identity(self):
        payload, _ = self._payload("false")
        self.assertEqual(payload["app"], "midaz")
        self.assertEqual(payload["env"], "beta")
        self.assertEqual(payload["repository"], "LerianStudio/midaz")
        self.assertEqual(payload["version"], "v4.1.0-beta.2")
        self.assertEqual(payload["revision"], "abc123def456")
        self.assertEqual(payload["previous"], "111222333444")
        self.assertIn("diff", payload)

    def test_default_run_says_the_registration_decides(self):
        _, result = self._payload("false")
        self.assertIn("registration", result.stdout)

    def test_opt_in_restores_the_transitional_override(self):
        payload, result = self._payload("true")
        self.assertEqual(payload["target_env"], "chaos-dev-st")
        self.assertIn("::warning", result.stdout)
        self.assertIn("overrides the registration", result.stdout)

    def test_opt_in_with_empty_target_env_sends_nothing(self):
        result = self.runner.run(
            PAYLOAD_SCRIPT, SEND_TARGET_ENV="true", **{**PAYLOAD_ENV, "TARGET_ENV": ""}
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads((self.runner.dir / "payload.json").read_text(encoding="utf-8"))
        self.assertNotIn("target_env", payload)


WEBHOOK_ENV = {
    "CONTROLLER_URL": "https://controller.invalid",
    "CURL_TIMEOUT": "960",
    "WEBHOOK_TOKEN": "t0ken",
    "APP": "midaz",
    "VERSION": "v4.1.0-beta.2",
    "ENV": "beta",
    "TARGET_ENV": "chaos-dev-st",
    "SEND_TARGET_ENV": "false",
}


@unittest.skipUnless(BASH, "requires bash 4+")
class VerdictTests(unittest.TestCase):
    """Not every non-analysis_completed status is a failure."""

    def setUp(self):
        self.runner = ScriptRunner(self)
        (self.runner.dir / "payload.json").write_text("{}", encoding="utf-8")

    def respond(self, body, **overrides):
        env = {**WEBHOOK_ENV, "STUB_RESPONSE": json.dumps(body), **overrides}
        return self.runner.run(WEBHOOK_SCRIPT, prelude=CURL_STUB, **env)

    # ----------------- Passing outcomes -----------------

    def test_analysis_completed_with_tests_is_executed(self):
        r = self.respond({"status": "analysis_completed", "run_id": "r1", "k6": 3, "chaos": 2})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.outputs["outcome"], "executed")

    def test_analysis_completed_without_tests_is_skipped(self):
        r = self.respond({"status": "analysis_completed", "run_id": "r1", "k6": 0, "chaos": 0})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.outputs["outcome"], "skipped")

    def test_accepted_is_not_a_failure(self):
        """A channel configured for the authored suite alone, doing exactly what it
        was configured to do, used to be reported as a broken release."""
        r = self.respond({"status": "accepted", "run_id": "r2", "will_run": ["authored-e2e"]})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.outputs["outcome"], "accepted")
        self.assertEqual(r.outputs["will_run"], "authored-e2e")
        self.assertIn("authored suite runs as its own detached run", r.stdout)

    def test_no_applicable_stages_warns_loudly_but_passes(self):
        r = self.respond({"status": "no_applicable_stages", "run_id": "r3"})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.outputs["outcome"], "no_stages")
        self.assertIn("::warning", r.stdout)
        self.assertIn("validates nothing", r.stdout)

    # ----------------- Failing outcomes -----------------

    def test_analysis_failed_still_fails(self):
        r = self.respond({"status": "analysis_failed", "run_id": "r4"})
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.outputs["outcome"], "failed")

    def test_registration_refusal_still_fails(self):
        r = self.respond({"status": "refused", "reason": "no registration for channel beta"})
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.outputs["outcome"], "failed")

    def test_empty_response_fails_and_names_the_timeout(self):
        """The midaz failure: curl gave up client-side, so there was no status at
        all. The error must point at the timeout budget rather than at the app."""
        env = {**WEBHOOK_ENV, "STUB_RESPONSE": ""}
        r = self.runner.run(WEBHOOK_SCRIPT, prelude=CURL_STUB, **env)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.outputs["outcome"], "failed")
        self.assertIn("curl-timeout", r.stdout)

    # ----------------- Surface reporting -----------------

    def test_summary_credits_the_registration_when_not_overriding(self):
        r = self.respond({"status": "analysis_completed", "k6": 1, "chaos": 0})
        self.assertIn("Applications tab", r.step_summary)
        self.assertNotIn("chaos-dev-st", r.step_summary)

    def test_summary_names_the_override_when_overriding(self):
        r = self.respond({"status": "analysis_completed", "k6": 1, "chaos": 0},
                         SEND_TARGET_ENV="true")
        self.assertIn("chaos-dev-st", r.step_summary)
        self.assertIn("target_env override", r.step_summary)


class TimeoutBudgetTests(unittest.TestCase):
    def test_curl_timeout_default_exceeds_every_hop_it_fronts(self):
        """960s: bridge 780 < controller NEMOCLAW_TIMEOUT_SECONDS 900 < NPM edge and
        k8s ingress 960 <= this. Equal is not enough — the client must not give up
        first, which is exactly what produced an empty status after 900s."""
        block = ACTION.split("curl-timeout:", 1)[1].split("dry-run:", 1)[0]
        self.assertIn('default: "960"', block)


class ChannelInferenceTests(unittest.TestCase):
    """A bare semver is stable, and only a bare semver."""

    CASES = [
        ("v4.1.0-beta.2", "beta", "dev"),
        ("v4.1.0-beta2", "beta", "dev"),
        ("v2.0.0-rc.1", "rc", "stg"),
        ("v2.0.0-rc1", "rc", "stg"),
        ("v1.0.0-alpha.3", "beta", "dev"),
        ("v3.8.0", "stable", "prd"),
        ("3.8.0", "stable", "prd"),
        ("v1.2.3+20260812", "stable", "prd"),
    ]

    REFUSED = ["build-1234", "nightly", "v1.2.3.4", "v1x.2y.3z", "latest", "v1.2"]

    @unittest.skipUnless(BASH, "requires bash 4+")
    def _resolve(self, workflow, step, var, tag):
        script = extract_run_body(workflow, step)
        runner = ScriptRunner(self)
        return runner.run(script, **{var: tag, "REF_TYPE": "tag", "RELEASE_GIT_TAG": tag})

    def test_go_release_maps_every_known_tag_shape(self):
        for tag, env, base in self.CASES:
            with self.subTest(tag=tag):
                r = self._resolve(GO_RELEASE, "Resolve release tag, channel and base env",
                                  "REF_NAME", tag)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertEqual(r.outputs["release_env"], env)
                self.assertEqual(r.outputs["base_env"], base)

    def test_go_release_refuses_a_tag_that_says_nothing(self):
        """A guess that reaches production is not worth making."""
        for tag in self.REFUSED:
            with self.subTest(tag=tag):
                r = self._resolve(GO_RELEASE, "Resolve release tag, channel and base env",
                                  "REF_NAME", tag)
                self.assertEqual(r.returncode, 1, f"{tag} should not resolve a channel")
                self.assertNotIn("release_env=stable", r.github_output)

    def test_js_release_maps_every_known_tag_shape(self):
        for tag, env, base in self.CASES:
            with self.subTest(tag=tag):
                r = self._resolve(JS_RELEASE, "Resolve release channel and base env",
                                  "REF_NAME", tag)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertEqual(r.outputs["release_env"], env)
                self.assertEqual(r.outputs["base_env"], base)

    def test_js_release_refuses_a_tag_that_says_nothing(self):
        for tag in self.REFUSED:
            with self.subTest(tag=tag):
                r = self._resolve(JS_RELEASE, "Resolve release channel and base env",
                                  "REF_NAME", tag)
                self.assertEqual(r.returncode, 1, f"{tag} should not resolve a channel")


if __name__ == "__main__":
    unittest.main(verbosity=2)
