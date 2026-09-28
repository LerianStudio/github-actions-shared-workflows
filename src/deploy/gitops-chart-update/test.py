#!/usr/bin/env python3
"""Exercise the shipped plugin-isolation step without network or containers.

Usage: python3 src/deploy/gitops-chart-update/test.py
GITOPS_CHART_ACTION_PATH may select a historical action.yml for red/green replay.
Only Bash and Python's standard library are required; fixtures never use real HOME.
"""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ACTION = Path(os.environ.get("GITOPS_CHART_ACTION_PATH", str(Path(__file__).with_name("action.yml"))))
ROOT = Path(__file__).resolve().parents[3]
ISOLATE = "Isolate Helm plugins"


def steps():
    """Read top-level composite step blocks, matching the repository's test convention."""
    return re.findall(r"^    - name: ([^\n]+)\n(.*?)(?=^    - name: |\Z)",
                      ACTION.read_text(), flags=re.MULTILINE | re.DOTALL)


def run_body(name):
    block = dict(steps())[name]
    lines = block.split("      run: |\n", 1)[1].splitlines()
    body = []
    for line in lines:
        if line.strip() and not line.startswith("        "):
            break
        body.append(line[8:])
    return "\n".join(body)


def snapshot(root):
    return {str(path.relative_to(root)): path.read_bytes()
            for path in root.rglob("*") if path.is_file()}


class PluginIsolationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="gitops-plugin-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.runner_temp = self.root / "runner temp"
        self.runner_temp.mkdir()
        self.plugins = self.home / ".local/share/helm/plugins"
        # Different directory names declaring the same plugin reproduce the
        # persistent runner state. Neither directory belongs to this action.
        for name in ("helm-diff", "helm-diff_3.15.2_linux_amd64"):
            plugin = self.plugins / name
            plugin.mkdir(parents=True)
            (plugin / "plugin.yaml").write_text('name: diff\nversion: "3.15.2"\ncommand: /bin/true\n')
        self.registry = self.home / ".config/helm/registry/config.json"
        self.registry.parent.mkdir(parents=True)
        self.registry.write_text('{"auths":{"registry.example":{"auth":"fixture-only"}}}\n')
        self.env_file = self.root / "github-env"
        self.env_file.write_text("EXISTING_SETTING=keep\n")
        self.output = self.root / "github-output"
        self.output.write_text("has-changes=true\nlevel=patch\nroute=none\nsynced=false\n")
        # Do not inherit HELM_*, XDG_* or credentials from the developer machine.
        self.env = {
            "PATH": os.environ["PATH"], "HOME": str(self.home),
            "RUNNER_TEMP": str(self.runner_temp), "GITHUB_ENV": str(self.env_file),
            "GITHUB_OUTPUT": str(self.output), "HELM_REGISTRY_CONFIG": str(self.registry),
        }

    def isolate(self, env=None):
        result = subprocess.run(["bash", "--noprofile", "--norc", "-c", run_body(ISOLATE)],
                                env=env or self.env, cwd=self.root,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        # GITHUB_ENV is consumed by the runner between steps, not sourced as a
        # shell script (paths may contain spaces).
        values = dict(line.split("=", 1) for line in self.env_file.read_text().splitlines())
        self.assertEqual(set(values), {"EXISTING_SETTING", "HELM_PLUGINS"})
        self.assertEqual(values["EXISTING_SETTING"], "keep")
        return Path(values["HELM_PLUGINS"])

    def test_fresh_empty_directory_under_runner_temp(self):
        isolated = self.isolate()
        self.assertEqual(isolated.parent, self.runner_temp)
        self.assertTrue(isolated.is_dir())
        self.assertEqual(list(isolated.iterdir()), [])
        self.assertEqual(isolated.stat().st_mode & 0o777, 0o700)

    def test_duplicate_global_plugins_and_registry_are_untouched(self):
        before = snapshot(self.home)
        self.isolate()
        self.assertEqual(snapshot(self.home), before)

    def test_repeated_invocations_do_not_reuse_previous_plugins(self):
        first = self.isolate()
        sentinel = first / "previous-invocation"
        sentinel.write_text("do not reuse or delete\n")
        # Same job, including GITHUB_ENV's inherited value on the second call.
        second = self.isolate({**self.env, "HELM_PLUGINS": str(first)})
        self.assertNotEqual(first, second)
        self.assertEqual(second.parent, self.runner_temp)
        self.assertEqual(list(second.iterdir()), [])
        self.assertEqual(sentinel.read_text(), "do not reuse or delete\n")

    def test_inherited_plugin_path_is_replaced_not_cleaned(self):
        before = snapshot(self.home)
        isolated = self.isolate({**self.env, "HELM_PLUGINS": str(self.plugins)})
        self.assertNotEqual(isolated, self.plugins)
        self.assertEqual(snapshot(self.home), before)

    def test_output_state_and_registry_configuration_do_not_change(self):
        output_before = self.output.read_bytes()
        registry_before = self.registry.read_bytes()
        self.isolate()
        self.assertEqual(self.output.read_bytes(), output_before)
        self.assertEqual(self.registry.read_bytes(), registry_before)
        # Only HELM_PLUGINS is exported; registry, cache and config settings keep
        # their normal values, including a caller's explicit registry override.
        exported = [line.split("=", 1)[0] for line in self.env_file.read_text().splitlines()[1:]]
        self.assertEqual(exported, ["HELM_PLUGINS"])

    def test_failed_directory_creation_does_not_export_empty_path(self):
        before = self.env_file.read_bytes()
        env = {**self.env, "RUNNER_TEMP": str(self.root / "missing")}
        result = subprocess.run(["bash", "-c", run_body(ISOLATE)], env=env,
                                cwd=self.root, capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.env_file.read_bytes(), before)


class WorkflowContractTests(unittest.TestCase):
    def test_isolation_precedes_installer_and_every_helm_command(self):
        blocks = steps()
        names = [name for name, _ in blocks]
        self.assertIn(ISOLATE, names)
        isolation_index = names.index(ISOLATE)
        self.assertNotIn("      if:", dict(blocks)[ISOLATE])
        self.assertNotIn("continue-on-error:", dict(blocks)[ISOLATE])
        helm_steps = []
        for index, (name, block) in enumerate(blocks):
            if "helmfile/helmfile-action@" in block or (
                    "      run: |" in block and re.search(r"\bhelm(?:file)?\s", run_body(name))):
                helm_steps.append(name)
                self.assertLess(isolation_index, index, name)
            self.assertNotIn("HELM_PLUGINS:", block, "step env must not override GITHUB_ENV")
        self.assertIn("Set up helmfile", helm_steps)
        self.assertIn("Pull the chart", helm_steps)
        self.assertIn("Render every changed helmfile", helm_steps)

    def test_installer_still_skips_plugins_and_only_runs_version(self):
        setup = dict(steps())["Set up helmfile"]
        self.assertIn('        helm-plugins: ""\n', setup)
        self.assertIn("        helmfile-args: --version\n", setup)
        self.assertNotRegex(setup, r"helmfile-auto-init:\s*['\"]?true")

    def test_public_output_expressions_are_unchanged(self):
        outputs = ACTION.read_text().split("\noutputs:\n", 1)[1].split("\nruns:\n", 1)[0]
        self.assertEqual(re.findall(r"^  ([\w-]+):$", outputs, flags=re.MULTILINE),
                         ["synced", "has-changes", "level", "route"])
        self.assertEqual(re.findall(r"^    value: (.+)$", outputs, flags=re.MULTILINE), [
            "${{ steps.sync.outputs.synced || 'false' }}",
            "${{ steps.bump.outputs.has-changes }}",
            "${{ steps.bump.outputs.level }}",
            "${{ steps.deliver.outputs.route || 'none' }}",
        ])

    def test_ci_runs_regressions_and_gates_review_on_them(self):
        workflow = (ROOT / ".github/workflows/self-pr-validation.yml").read_text()
        self.assertIn("run: python3 src/deploy/gitops-chart-update/test.py", workflow)
        self.assertIn("      - gitops-chart-update-tests\n", workflow)


if __name__ == "__main__":
    unittest.main(verbosity=2)
