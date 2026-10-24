#!/usr/bin/env python3
"""Shape and behaviour tests for js-release.yml's permission_manifest_publish job.

The job is go-release's job adapted for a JS/TS repo. These tests pin the two
intended differences (opt-in default, lib-auth scope gate off) and guard the
rest against drift: the tag -> environment folder step must stay byte-identical
to go-release's, and is executed against a tag table so the mapping itself is
asserted (beta -> development, rc -> staging, stable -> production, anything
else -> nothing).
"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
JOB = "permission_manifest_publish"
FOLDER_STEP = "Determine environment folder from tag"
COMPOSITE = "LerianStudio/github-actions-shared-workflows/src/validate/permission-manifest-publish@v1"


def load(name):
    with open(REPO_ROOT / ".github" / "workflows" / name, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def workflow_call(doc):
    # PyYAML (YAML 1.1) reads the bare `on:` key as the boolean True.
    return (doc.get("on") or doc.get(True))["workflow_call"]


def step(job, name):
    for candidate in job["steps"]:
        if candidate.get("name") == name:
            return candidate
    raise AssertionError(f"step not found: {name}")


def composite_step(job):
    for candidate in job["steps"]:
        if str(candidate.get("uses", "")).startswith(COMPOSITE.split("@")[0]):
            return candidate
    raise AssertionError("permission-manifest-publish composite step not found")


JS = load("js-release.yml")
GO = load("go-release.yml")
JS_JOB = JS["jobs"][JOB]
GO_JOB = GO["jobs"][JOB]


def resolve_folder(tag, component_tags="false"):
    body = step(JS_JOB, FOLDER_STEP)["run"]
    with tempfile.TemporaryDirectory() as temp_dir:
        output = Path(temp_dir) / "output"
        output.write_text("", encoding="utf-8")
        subprocess.run(
            ["bash", "-c", body],
            env={
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "GITHUB_REF": f"refs/tags/{tag}",
                "GITHUB_OUTPUT": str(output),
                "MANIFEST_COMPONENT_TAGS": component_tags,
            },
            text=True,
            capture_output=True,
            check=True,
        )
        for line in output.read_text(encoding="utf-8").splitlines():
            if line.startswith("folder="):
                return line.split("=", 1)[1]
    raise AssertionError("folder output not written")


class JobShape(unittest.TestCase):
    def test_publish_is_opt_in(self):
        spec = workflow_call(JS)["inputs"]["run_manifest_publish"]
        self.assertEqual(spec["type"], "boolean")
        self.assertIs(spec["default"], False)

    def test_job_runs_only_on_tag_push_when_enabled(self):
        condition = JS_JOB["if"]
        self.assertIn("github.ref_type == 'tag'", condition)
        self.assertIn("inputs.run_manifest_publish", condition)

    def test_job_never_blocks_the_release(self):
        self.assertIs(JS_JOB["continue-on-error"], True)

    def test_oidc_permissions_and_role_secret(self):
        self.assertEqual(JS_JOB["permissions"], {"id-token": "write", "contents": "read"})
        secrets = workflow_call(JS)["secrets"]
        self.assertIn("AWS_INIT_DATA_ROLE_ARN", secrets)
        self.assertIs(secrets["AWS_INIT_DATA_ROLE_ARN"]["required"], False)

    def test_lib_auth_gate_is_off(self):
        with_ = composite_step(JS_JOB)["with"]
        self.assertEqual(str(with_["require-lib-auth"]), "false")
        self.assertNotIn("go-mod-path", with_)

    def test_same_composite_ref_as_go_release(self):
        self.assertEqual(composite_step(JS_JOB)["uses"], composite_step(GO_JOB)["uses"])

    # Everything but the composite's inputs must match go-release step for step:
    # same guards on the credential and publish steps, same role, same region.
    def test_steps_match_go_release(self):
        js_steps = [s for s in JS_JOB["steps"] if "with" not in s or "role-to-assume" in s["with"]]
        go_steps = [s for s in GO_JOB["steps"] if "with" not in s or "role-to-assume" in s["with"]]
        self.assertEqual(js_steps, go_steps)
        self.assertEqual(composite_step(JS_JOB)["if"], composite_step(GO_JOB)["if"])
        self.assertEqual(JS_JOB["env"], GO_JOB["env"])
        self.assertEqual(JS_JOB["environment"], GO_JOB["environment"])


class TagToFolder(unittest.TestCase):
    CASES = [
        ("v1.2.3-beta.4", "false", "development"),
        ("v1.2.3-rc.2", "false", "staging"),
        ("v1.2.3", "false", "production"),
        ("v01.2.3", "false", ""),
        ("v1.2.3-hotfix", "false", ""),
        ("v1.2.3-alpha.1", "false", ""),
        ("console-v1.2.3", "false", ""),
        ("console-v1.2.3", "true", "production"),
        ("console-v1.2.3-rc.1", "true", "staging"),
        ("Console-v1.2.3", "true", ""),
    ]

    def test_mapping(self):
        for tag, component_tags, want in self.CASES:
            with self.subTest(tag=tag, component_tags=component_tags):
                self.assertEqual(resolve_folder(tag, component_tags), want)


if __name__ == "__main__":
    unittest.main(verbosity=2)
