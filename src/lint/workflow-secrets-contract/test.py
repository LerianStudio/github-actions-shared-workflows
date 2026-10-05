#!/usr/bin/env python3
"""Run the shipped check against synthetic workflow trees.

Usage: python3 src/lint/workflow-secrets-contract/test.py

Each case writes a throwaway workflows directory and asserts the exit status
and the message, so a regression in the parser shows up as a failing test
rather than as a lint that quietly stops finding things.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest

CHECK = Path(__file__).with_name("check.py")

CALLEE_WITH_CONTRACT = """\
name: Callee
on:
  workflow_call:
    secrets:
      MANAGE_TOKEN:
        required: false
      SLACK_WEBHOOK_URL:
        required: false
jobs:
  noop:
    runs-on: ubuntu-latest
    steps:
      - run: 'true'
"""

CALLEE_WITHOUT_CONTRACT = """\
name: Callee
on:
  workflow_call: {}
jobs:
  noop:
    runs-on: ubuntu-latest
    steps:
      - run: 'true'
"""


class WorkflowSecretsContractTests(unittest.TestCase):
    def run_check(self, caller, callee=CALLEE_WITH_CONTRACT,
                  callee_name="callee.yml", absolute_dir=False):
        with tempfile.TemporaryDirectory() as tmp:
            workflows = Path(tmp) / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / callee_name).write_text(callee)
            (workflows / "caller.yml").write_text(textwrap.dedent(caller))
            env = dict(os.environ, WORKFLOWS_DIR=(
                str(workflows) if absolute_dir else ".github/workflows"))
            return subprocess.run(
                ["python3", str(CHECK)],
                cwd=tmp, env=env, capture_output=True, text=True,
            )

    # ---- accepted shapes ----

    def test_full_named_forward_passes(self):
        result = self.run_check("""\
            name: Caller
            on: [push]
            jobs:
              call:
                uses: ./.github/workflows/callee.yml
                secrets:
                  MANAGE_TOKEN: ${{ secrets.MANAGE_TOKEN }}
                  SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
            """)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_inherit_is_allowed_when_the_callee_declares_nothing(self):
        result = self.run_check("""\
            name: Caller
            on: [push]
            jobs:
              call:
                uses: ./.github/workflows/callee.yml
                secrets: inherit
            """, callee=CALLEE_WITHOUT_CONTRACT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_a_remote_call_is_not_this_check_s_business(self):
        result = self.run_check("""\
            name: Caller
            on: [push]
            jobs:
              call:
                uses: LerianStudio/other-repo/.github/workflows/callee.yml@v1
                secrets: inherit
            """)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    # ---- rejected shapes ----

    def test_inherit_into_a_declared_contract_fails(self):
        result = self.run_check("""\
            name: Caller
            on: [push]
            jobs:
              call:
                uses: ./.github/workflows/callee.yml
                secrets: inherit
            """)
        self.assertEqual(result.returncode, 1)
        self.assertIn("must be forwarded by name", result.stdout)

    def test_partial_forward_fails_and_names_the_missing_secret(self):
        result = self.run_check("""\
            name: Caller
            on: [push]
            jobs:
              call:
                uses: ./.github/workflows/callee.yml
                secrets:
                  MANAGE_TOKEN: ${{ secrets.MANAGE_TOKEN }}
            """)
        self.assertEqual(result.returncode, 1)
        self.assertIn("SLACK_WEBHOOK_URL", result.stdout)

    def test_no_secrets_key_at_all_fails(self):
        """The quietest shape: the job simply never mentions secrets."""
        result = self.run_check("""\
            name: Caller
            on: [push]
            jobs:
              call:
                uses: ./.github/workflows/callee.yml
            """)
        self.assertEqual(result.returncode, 1)
        self.assertIn("forwards nothing", result.stdout)

    # ---- shapes that defeat a line-by-line scanner ----

    def test_trailing_comment_on_uses_is_still_matched(self):
        result = self.run_check("""\
            name: Caller
            on: [push]
            jobs:
              call:
                uses: ./.github/workflows/callee.yml # the scan
                secrets: inherit
            """)
        self.assertEqual(result.returncode, 1)
        self.assertIn("must be forwarded by name", result.stdout)

    def test_secrets_declared_before_uses_is_still_matched(self):
        """YAML mappings are unordered; `secrets:` may precede `uses:`."""
        result = self.run_check("""\
            name: Caller
            on: [push]
            jobs:
              call:
                secrets: inherit
                uses: ./.github/workflows/callee.yml
            """)
        self.assertEqual(result.returncode, 1)
        self.assertIn("must be forwarded by name", result.stdout)

    def test_a_mixed_case_filename_is_still_matched(self):
        """`Callee.yml` is a valid workflow name; it must not slip through."""
        result = self.run_check("""\
            name: Caller
            on: [push]
            jobs:
              call:
                uses: ./.github/workflows/Callee.yml
                secrets: inherit
            """, callee_name="Callee.yml")
        self.assertEqual(result.returncode, 1)
        self.assertIn("must be forwarded by name", result.stdout)

    def test_an_absolute_workflows_dir_still_matches_local_calls(self):
        """`uses:` is repository-relative regardless of where files are read from."""
        result = self.run_check("""\
            name: Caller
            on: [push]
            jobs:
              call:
                uses: ./.github/workflows/callee.yml
                secrets: inherit
            """, absolute_dir=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("must be forwarded by name", result.stdout)

    def test_the_dollar_prefix_form_is_still_matched(self):
        """`$/` is GitHub's recommended same-repository form on github.com."""
        result = self.run_check("""\
            name: Caller
            on: [push]
            jobs:
              call:
                uses: $/.github/workflows/callee.yml
                secrets: inherit
            """)
        self.assertEqual(result.returncode, 1)
        self.assertIn("must be forwarded by name", result.stdout)

    def test_a_full_forward_with_the_dollar_prefix_passes(self):
        result = self.run_check("""\
            name: Caller
            on: [push]
            jobs:
              call:
                uses: $/.github/workflows/callee.yml
                secrets:
                  MANAGE_TOKEN: ${{ secrets.MANAGE_TOKEN }}
                  SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
            """)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_a_later_job_does_not_mask_an_earlier_violation(self):
        result = self.run_check("""\
            name: Caller
            on: [push]
            jobs:
              bad:
                uses: ./.github/workflows/callee.yml
                secrets: inherit
              good:
                uses: ./.github/workflows/callee.yml
                secrets:
                  MANAGE_TOKEN: ${{ secrets.MANAGE_TOKEN }}
                  SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
            """)
        self.assertEqual(result.returncode, 1)
        self.assertIn("job `bad`", result.stdout)
        self.assertNotIn("job `good`", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
