#!/usr/bin/env python3
"""Behavioural tests for the permission-manifest-publish composite action.

Mirrors the extract/execute/parse harness used by
src/validate/breaking-change-guard/test-workflow.py: the embedded `run: |`
script is pulled out of action.yml by step name, executed in a throwaway
workspace with a controlled env, and its GITHUB_OUTPUT + stdout are asserted.

All publish assertions run in dry-run (DRY_RUN=true) so no AWS call is made,
except the two cases that deliberately stub a fake `aws` binary on PATH to
exercise the real success / failure branches.
"""

import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ACTION_PATH = Path(__file__).resolve().parent / "action.yml"
ACTION = ACTION_PATH.read_text(encoding="utf-8")

STEP_NAME = "Detect manifest and publish to the RI catalog"

# A go.mod with a DIRECT lib-auth dependency clears the scope gate.
GO_MOD_IN_SCOPE = textwrap.dedent(
    """\
    module github.com/LerianStudio/example

    go 1.26

    require github.com/LerianStudio/lib-auth/v2 v2.0.0
    """
)

# A go.mod with no lib-auth dependency is out of scope.
GO_MOD_OUT_OF_SCOPE = textwrap.dedent(
    """\
    module github.com/LerianStudio/example

    go 1.26

    require github.com/LerianStudio/lib-commons/v5 v5.0.0
    """
)


def manifest(service):
    return textwrap.dedent(
        f"""\
        service: {service}
        permissions:
          - resource: account
            actions: [read]
        """
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
    for line in lines[start + 1:]:
        if line.strip() and indentation(line) <= run_indent:
            break
        body.append(line)
    return textwrap.dedent("\n".join(body)).rstrip() + "\n"


def parse_github_output(output):
    values = {}
    for line in output.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value  # last write wins, matching GitHub Actions
    return values


RUN_BODY = extract_run_body(ACTION, STEP_NAME)


def write_fake_aws(bin_dir, exit_code):
    """Drop a fake `aws` on PATH so the non-dry-run branches are deterministic."""
    aws = bin_dir / "aws"
    aws.write_text(f'#!/usr/bin/env bash\nexit {exit_code}\n', encoding="utf-8")
    aws.chmod(aws.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def run_publish(files, env_overrides=None, fake_aws=None):
    """Run the extracted publish script in a fresh workspace.

    files: {relative_path: contents} written into the workspace.
    env_overrides: extra/override env for the action.
    fake_aws: None (rely on dry-run), or an int exit code for a stubbed `aws`.
    Returns (CompletedProcess, outputs_dict).
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Path(temp_dir)
        for rel, contents in files.items():
            path = workspace / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents, encoding="utf-8")

        output_path = workspace / "github-output"
        output_path.write_text("", encoding="utf-8")
        # Provision GITHUB_ENV / GITHUB_STEP_SUMMARY too: if a future edit to the
        # action appends to either, an unset var would be an ambiguous redirect and
        # fail the assertions for the wrong reason. Point both at workspace files.
        env_path = workspace / "github-env"
        env_path.write_text("", encoding="utf-8")
        summary_path = workspace / "github-step-summary"
        summary_path.write_text("", encoding="utf-8")

        path_value = os.environ.get("PATH", "/usr/bin:/bin")
        if fake_aws is not None:
            bin_dir = workspace / ".fakebin"
            bin_dir.mkdir()
            write_fake_aws(bin_dir, fake_aws)
            path_value = f"{bin_dir}:{path_value}"

        env = {
            "PATH": path_value,
            "HOME": str(workspace),
            "GITHUB_OUTPUT": str(output_path),
            "GITHUB_ENV": str(env_path),
            "GITHUB_STEP_SUMMARY": str(summary_path),
            "GO_MOD_PATH": "go.mod",
            "S3_BUCKET": "lerian-casdoor-init-data",
            "S3_PREFIX": "permissions",
            "AWS_REGION": "us-east-2",
            "ENVIRONMENT": "development",
            "DRY_RUN": "true",
        }
        if env_overrides:
            env.update(env_overrides)

        result = subprocess.run(
            ["bash", "-c", RUN_BODY],
            cwd=workspace,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        outputs = parse_github_output(output_path.read_text(encoding="utf-8"))
        return result, outputs


class PublishEveryManifest(unittest.TestCase):
    def assertExitZero(self, result):
        self.assertEqual(
            result.returncode,
            0,
            msg=f"expected exit 0 (best-effort)\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    # (a) Two manifests in different dirs -> two publishes, correct per-service keys.
    #     Path order (components/a, components/z) is deliberately the REVERSE of
    #     service-name order (zeta, alpha) so the assertions pin the sort key to the
    #     manifest PATH, not the service name.
    def test_two_manifests_publish_both(self):
        result, out = run_publish(
            {
                "go.mod": GO_MOD_IN_SCOPE,
                "components/a/permissions.yaml": manifest("zeta"),
                "components/z/permissions.yaml": manifest("alpha"),
            }
        )
        self.assertExitZero(result)
        self.assertEqual(out.get("state"), "dryrun")
        self.assertEqual(out.get("published_count"), "2")
        # Ordered by PATH (components/a before components/z), NOT by service name.
        self.assertEqual(out.get("services"), "zeta,alpha")
        self.assertEqual(
            out.get("s3_keys"),
            "development/permissions/zeta.yaml,development/permissions/alpha.yaml",
        )
        # Backward-compat scalars reflect the FIRST (path-sorted) publish.
        self.assertEqual(out.get("service"), "zeta")
        self.assertEqual(out.get("s3_key"), "development/permissions/zeta.yaml")
        # Two distinct dry-run targets logged.
        self.assertIn(
            "would publish components/a/permissions.yaml -> "
            "s3://lerian-casdoor-init-data/development/permissions/zeta.yaml",
            result.stdout,
        )
        self.assertIn(
            "would publish components/z/permissions.yaml -> "
            "s3://lerian-casdoor-init-data/development/permissions/alpha.yaml",
            result.stdout,
        )

    # (b) Duplicate service across two manifests -> loud collision, dup skipped.
    def test_duplicate_service_is_loud_and_skipped(self):
        result, out = run_publish(
            {
                "go.mod": GO_MOD_IN_SCOPE,
                "components/a/permissions.yaml": manifest("midaz"),
                "components/b/permissions.yaml": manifest("midaz"),
            }
        )
        self.assertExitZero(result)
        # Only the first landed; the duplicate is not double-counted.
        self.assertEqual(out.get("published_count"), "1")
        self.assertEqual(out.get("services"), "midaz")
        self.assertEqual(out.get("state"), "dryrun")
        # Compat scalars must point at the ACCEPTED manifest, not the skipped dup.
        self.assertEqual(out.get("service"), "midaz")
        self.assertEqual(out.get("s3_key"), "development/permissions/midaz.yaml")
        # Collision is visible in the log as a warning naming the service.
        self.assertIn("::warning", result.stdout)
        self.assertIn("Duplicate service 'midaz'", result.stdout)

    # (c) Single manifest -> unchanged behavior + backward-compat scalars.
    def test_single_manifest_unchanged(self):
        result, out = run_publish(
            {
                "go.mod": GO_MOD_IN_SCOPE,
                "permissions.yaml": manifest("br-sisbajud"),
            }
        )
        self.assertExitZero(result)
        self.assertEqual(out.get("state"), "dryrun")
        self.assertEqual(out.get("published_count"), "1")
        self.assertEqual(out.get("service"), "br-sisbajud")
        self.assertEqual(out.get("s3_key"), "development/permissions/br-sisbajud.yaml")
        self.assertEqual(out.get("services"), "br-sisbajud")
        self.assertEqual(out.get("s3_keys"), "development/permissions/br-sisbajud.yaml")

    # (d) Zero qualifying manifests -> skip.
    def test_zero_manifests_skip(self):
        result, out = run_publish({"go.mod": GO_MOD_IN_SCOPE})
        self.assertExitZero(result)
        self.assertEqual(out.get("state"), "skip")
        self.assertEqual(out.get("published_count"), "0")
        self.assertEqual(out.get("service"), "")
        self.assertEqual(out.get("services"), "")

    def test_out_of_scope_no_lib_auth_skip(self):
        result, out = run_publish(
            {
                "go.mod": GO_MOD_OUT_OF_SCOPE,
                "permissions.yaml": manifest("midaz"),
            }
        )
        self.assertExitZero(result)
        self.assertEqual(out.get("state"), "skip")

    def test_empty_environment_skips_before_publish(self):
        result, out = run_publish(
            {
                "go.mod": GO_MOD_IN_SCOPE,
                "permissions.yaml": manifest("midaz"),
            },
            env_overrides={"ENVIRONMENT": ""},
        )
        self.assertExitZero(result)
        self.assertEqual(out.get("state"), "skip")
        self.assertEqual(out.get("published_count"), "0")

    def test_empty_service_value_skipped(self):
        result, out = run_publish(
            {
                "go.mod": GO_MOD_IN_SCOPE,
                "permissions.yaml": "service:\npermissions:\n  - resource: account\n",
            }
        )
        self.assertExitZero(result)
        self.assertEqual(out.get("state"), "skip")
        self.assertEqual(out.get("published_count"), "0")

    # Real (non-dry-run) success branch via a stubbed `aws` that exits 0.
    def test_real_publish_success_two_manifests(self):
        result, out = run_publish(
            {
                "go.mod": GO_MOD_IN_SCOPE,
                "components/a/permissions.yaml": manifest("midaz"),
                "components/b/permissions.yaml": manifest("tracer"),
            },
            env_overrides={"DRY_RUN": "false"},
            fake_aws=0,
        )
        self.assertExitZero(result)
        self.assertEqual(out.get("state"), "published")
        self.assertEqual(out.get("published_count"), "2")
        self.assertEqual(out.get("services"), "midaz,tracer")

    # Upload hiccup on every manifest -> best-effort skip, never fails the release.
    def test_real_publish_all_fail_degrades_to_skip(self):
        result, out = run_publish(
            {
                "go.mod": GO_MOD_IN_SCOPE,
                "components/a/permissions.yaml": manifest("midaz"),
                "components/b/permissions.yaml": manifest("tracer"),
            },
            env_overrides={"DRY_RUN": "false"},
            fake_aws=1,
        )
        self.assertExitZero(result)
        self.assertEqual(out.get("state"), "skip")
        self.assertEqual(out.get("published_count"), "0")
        self.assertIn("::warning", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
