#!/usr/bin/env python3
"""Behavioural tests for the permission-manifest-publish composite action.

Mirrors the extract/execute/parse harness used by
src/validate/breaking-change-guard/test-workflow.py: the embedded `run: |`
scripts are pulled out of action.yml by step name and executed in a throwaway
workspace with a controlled env, chained the way the runner chains them
(detect -> validate -> publish, each gated on detect's `proceed` output, and
publish skipped when validate fails). GITHUB_OUTPUT + stdout are asserted.

The validate step runs the REAL validator (validator/, built with the local Go
toolchain against its pinned lib-auth), so these tests need `go` on PATH and
access to the Go module proxy (or a warm module cache).

All publish assertions run in dry-run (DRY_RUN=true) so no AWS call is made,
except the cases that deliberately stub a fake `aws` binary on PATH to
exercise the real success / failure branches.
"""

import os
import re
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ACTION_PATH = Path(__file__).resolve().parent / "action.yml"
ACTION = ACTION_PATH.read_text(encoding="utf-8")

DETECT_STEP = "Detect permission manifests"
VALIDATE_STEP = "Validate permission manifests"
PUBLISH_STEP = "Publish permission manifests to the RI catalog"
VALIDATOR_DIR = Path(__file__).resolve().parent / "validator"

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
    """A manifest that passes lib-auth's DeclarationManifest.Validate()."""
    return textwrap.dedent(
        f"""\
        service: {service}
        version: 1
        roles:
          - name: viewer
        permissions:
          - resource: account
            action: get
            effect: allow
            roles: [viewer]
        """
    )


# The schema-drift shape that reached the catalog before validation existed
# (reporter, br-ccs): no version, plural `actions:`, no effect, and a role that
# is granted but never declared. Qualifies for detection, fails Validate().
def old_schema_manifest(service):
    return textwrap.dedent(
        f"""\
        service: {service}
        permissions:
          - resource: account
            actions: [read]
            roles: [{service}-viewer]
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
    """Parse GITHUB_OUTPUT, including the `name<<DELIM ... DELIM` multiline form."""
    values = {}
    lines = output.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        if "<<" in line and ("=" not in line or line.index("<<") < line.index("=")):
            key, delim = line.split("<<", 1)
            body = []
            while index < len(lines) and lines[index] != delim:
                body.append(lines[index])
                index += 1
            index += 1  # skip the closing delimiter
            values[key] = "\n".join(body)
        elif "=" in line:
            key, value = line.split("=", 1)
            values[key] = value  # last write wins, matching GitHub Actions
    return values


DETECT_BODY = extract_run_body(ACTION, DETECT_STEP)
VALIDATE_BODY = extract_run_body(ACTION, VALIDATE_STEP)
PUBLISH_BODY = extract_run_body(ACTION, PUBLISH_STEP)


def go_env(name):
    return subprocess.run(
        ["go", "env", name], text=True, capture_output=True, check=True
    ).stdout.strip()


# HOME is a throwaway per test, so point Go at the host caches explicitly — a
# cold module/build cache per test would rebuild lib-auth every time.
GO_CACHE_ENV = {name: go_env(name) for name in ("GOCACHE", "GOMODCACHE", "GOPATH")}


def write_fake_aws(bin_dir, exit_code):
    """Drop a fake `aws` on PATH so the non-dry-run branches are deterministic."""
    aws = bin_dir / "aws"
    aws.write_text(f'#!/usr/bin/env bash\nexit {exit_code}\n', encoding="utf-8")
    aws.chmod(aws.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


class PipelineResult:
    """The chained run: combined stdout, the exit code of the step that decided
    the outcome (a failing validate step fails the action), and which steps ran."""

    def __init__(self):
        self.stdout = ""
        self.stderr = ""
        self.returncode = 0
        self.ran = []


def run_publish(files, env_overrides=None, fake_aws=None):
    """Run the extracted detect -> validate -> publish scripts in a fresh workspace.

    files: {relative_path: contents} written into the workspace.
    env_overrides: extra/override env for the action.
    fake_aws: None (rely on dry-run), or an int exit code for a stubbed `aws`.
    Returns (PipelineResult, outputs_dict) where outputs_dict is the action's
    outputs as action.yml resolves them (publish first, falling back to detect).
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

        runner_temp = workspace / ".runner-temp"
        runner_temp.mkdir()

        env = {
            "PATH": path_value,
            "HOME": str(workspace),
            "RUNNER_TEMP": str(runner_temp),
            "GITHUB_OUTPUT": str(output_path),
            "GITHUB_ENV": str(env_path),
            "GITHUB_STEP_SUMMARY": str(summary_path),
            "VALIDATOR_DIR": str(VALIDATOR_DIR),
            "GOFLAGS": "-mod=readonly",
            "GOWORK": "off",
            **GO_CACHE_ENV,
            "GO_MOD_PATH": "go.mod",
            "S3_BUCKET": "lerian-casdoor-init-data",
            "S3_PREFIX": "permissions",
            "AWS_REGION": "us-east-2",
            "ENVIRONMENT": "development",
            "DRY_RUN": "true",
        }
        if env_overrides:
            env.update(env_overrides)

        result = PipelineResult()

        def step(name, body, step_env):
            # Each step gets its own GITHUB_OUTPUT, as on the runner.
            output_path.write_text("", encoding="utf-8")
            completed = subprocess.run(
                ["bash", "-c", body],
                cwd=workspace,
                env=step_env,
                text=True,
                capture_output=True,
                check=False,
            )
            result.ran.append(name)
            result.stdout += completed.stdout
            result.stderr += completed.stderr
            result.returncode = completed.returncode
            return completed.returncode, parse_github_output(
                output_path.read_text(encoding="utf-8")
            )

        code, detect = step("detect", DETECT_BODY, env)
        publish = {}
        if code == 0 and detect.get("proceed") == "true":
            chained = {**env, "MANIFESTS": detect.get("manifests", "")}
            code, _ = step("validate", VALIDATE_BODY, chained)
            if code == 0:
                _, publish = step("publish", PUBLISH_BODY, chained)

        # Resolve the action outputs exactly as action.yml declares them.
        outputs = {
            "state": publish.get("state") or detect.get("state", ""),
            "service": publish.get("service", ""),
            "s3_key": publish.get("s3_key", ""),
            "services": publish.get("services", ""),
            "s3_keys": publish.get("s3_keys", ""),
            "published_count": publish.get("published_count") or "0",
        }
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

    # An empty service: value used to be skipped by the publish step; it is now
    # rejected one step earlier, by validation, and nothing is published.
    def test_empty_service_value_fails_validation(self):
        result, out = run_publish(
            {
                "go.mod": GO_MOD_IN_SCOPE,
                "permissions.yaml": "service:\npermissions:\n  - resource: account\n",
            }
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("publish", result.ran)
        self.assertIn("service must not be empty", result.stdout)
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


class ValidateBeforePublish(unittest.TestCase):
    """A manifest the tenant-manager would reject must never reach the bucket:
    validation runs the same yaml.Unmarshal + DeclarationManifest.Validate()
    the tenant-manager runs, and any failure stops the action before publish."""

    def test_old_schema_manifest_fails_and_publishes_nothing(self):
        result, out = run_publish(
            {
                "go.mod": GO_MOD_IN_SCOPE,
                "permissions.yaml": old_schema_manifest("reporter"),
            },
            env_overrides={"DRY_RUN": "false"},
            fake_aws=0,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.ran, ["detect", "validate"])
        self.assertIn("::error file=./permissions.yaml", result.stdout)
        self.assertIn("version must be a positive integer", result.stdout)
        self.assertIn('references undeclared role "reporter-viewer"', result.stdout)
        self.assertEqual(out.get("state"), "")
        self.assertEqual(out.get("published_count"), "0")

    # One bad manifest in a monorepo blocks the whole publish, valid ones too:
    # the catalog keeps their previous objects until the repo is fixed.
    def test_one_invalid_manifest_blocks_every_publish(self):
        result, out = run_publish(
            {
                "go.mod": GO_MOD_IN_SCOPE,
                "components/a/permissions.yaml": manifest("midaz"),
                "components/b/permissions.yaml": old_schema_manifest("br-ccs"),
            },
            env_overrides={"DRY_RUN": "false"},
            fake_aws=0,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("publish", result.ran)
        self.assertIn("valid: ./components/a/permissions.yaml", result.stdout)
        self.assertIn("::error file=./components/b/permissions.yaml", result.stdout)
        self.assertIn("1 of 2 permission manifest(s) invalid", result.stdout)
        self.assertEqual(out.get("published_count"), "0")

    # Validation is not a real-upload-only gate: a dry-run fails the same way,
    # so a preview never reports a manifest as publishable when it is not.
    def test_dry_run_also_validates(self):
        result, _ = run_publish(
            {
                "go.mod": GO_MOD_IN_SCOPE,
                "permissions.yaml": old_schema_manifest("reporter"),
            }
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("would publish", result.stdout)

    def test_unparsable_yaml_fails(self):
        result, _ = run_publish(
            {
                "go.mod": GO_MOD_IN_SCOPE,
                "permissions.yaml": "service: broken\npermissions: [\n",
            }
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("parse yaml manifest", result.stdout)

    # A validator that cannot be built checked nothing: fail closed.
    def test_unbuildable_validator_fails_closed(self):
        result, _ = run_publish(
            {
                "go.mod": GO_MOD_IN_SCOPE,
                "permissions.yaml": manifest("midaz"),
            },
            env_overrides={"VALIDATOR_DIR": "/nonexistent/validator"},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("publish", result.ran)
        self.assertIn("Could not build the manifest validator", result.stdout)

    # Skips never pay for the toolchain: validation only runs once detect says so.
    def test_skip_paths_do_not_validate(self):
        result, out = run_publish(
            {
                "go.mod": GO_MOD_OUT_OF_SCOPE,
                "permissions.yaml": old_schema_manifest("reporter"),
            }
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.ran, ["detect"])
        self.assertEqual(out.get("state"), "skip")

    def test_validation_steps_are_gated_on_detect(self):
        for name in ("Set up Go for the manifest validator", VALIDATE_STEP, PUBLISH_STEP):
            self.assertIn(
                "if: steps.detect.outputs.proceed == 'true'",
                extract_step(ACTION, name),
                msg=f"step {name!r} must only run when detect proceeds",
            )


class RegionConfiguration(unittest.TestCase):
    """The RI catalog bucket lives in sa-east-1, so the publisher must target
    that region. test.py runs the extracted bash body directly and injects
    AWS_REGION itself, bypassing the Actions input-defaulting layer — so the
    metadata default is asserted against action.yml text (guarding a silent
    revert), while the caller-override passthrough is exercised end-to-end
    through the dry-run command.
    """

    def test_action_default_region_is_sa_east_1(self):
        # The `aws-region` input default is what every caller that omits the
        # input inherits; it MUST be the bucket's real region (sa-east-1).
        m = re.search(r'aws-region:.*?default:\s*"([^"]+)"', ACTION, re.DOTALL)
        self.assertIsNotNone(m, "aws-region input default not found in action.yml")
        self.assertEqual(m.group(1), "sa-east-1")

    def test_explicit_region_override_passes_through(self):
        # A caller-supplied region must reach the `aws s3 cp` command verbatim,
        # never silently replaced by the default.
        result, out = run_publish(
            {
                "go.mod": GO_MOD_IN_SCOPE,
                "permissions.yaml": manifest("br-sisbajud"),
            },
            env_overrides={"AWS_REGION": "eu-west-1"},
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(out.get("state"), "dryrun")
        self.assertIn("--region eu-west-1", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
