#!/usr/bin/env python3
"""Offline regression tests: python3 test-tooling.py (requires PyYAML and Helm).

Execute the actual composite's isolation step, then real Helm commands against
an intentionally contaminated HOME. No downloads, cluster, or plugin installs.
Set HELM_BIN to exercise another installed Helm version.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml


ACTION = Path(__file__).with_name("action.yml")
STEPS = yaml.safe_load(ACTION.read_text())["runs"]["steps"]
HELM = shutil.which(os.environ.get("HELM_BIN", "helm"))


class HelmToolingTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(HELM, "Install Helm or set HELM_BIN before running tests")
        self.temp = tempfile.TemporaryDirectory(prefix="gitops-chart-tooling-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.plugins = self.home / ".local/share/helm/plugins"
        for name in ("diff", "helm-diff-linux-amd64"):
            plugin = self.plugins / name
            plugin.mkdir(parents=True)
            (plugin / "plugin.yaml").write_text(
                'name: diff\nversion: "1.0.0"\nusage: fixture\n'
                'description: duplicate-name fixture\ncommand: /bin/true\n'
            )
        self.before = {str(p.relative_to(self.home)): p.read_bytes()
                       for p in self.home.rglob("*") if p.is_file()}
        self.runner_temp = self.root / "runner temp"
        self.runner_temp.mkdir()
        self.env_file = self.root / "github-env"
        self.env_file.touch()
        # Never inspect or modify the host's real Helm/plugin/registry state.
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith(("HELM_", "XDG_"))}
        self.env.update(HOME=str(self.home), RUNNER_TEMP=str(self.runner_temp),
                        GITHUB_ENV=str(self.env_file),
                        HELM_PLUGINS=str(self.plugins))

    def helm(self, *args, env=None):
        if HELM is None:
            self.fail("Install Helm or set HELM_BIN before running tests")
        return subprocess.run([HELM, *args], env=env or self.env,
                              text=True, capture_output=True, check=False)

    def isolate(self):
        step = next((s for s in STEPS
                     if s.get("name") == "Isolate Helm plugins"), None)
        if step is None:
            self.fail("Missing isolation before Helm setup")
        setup = next(s for s in STEPS if s.get("name") == "Set up helmfile")
        self.assertLess(STEPS.index(step), STEPS.index(setup))
        result = subprocess.run(["bash", "--noprofile", "--norc", "-e",
                                 "-o", "pipefail", "-c", step["run"]],
                                env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        # Model the runner's GITHUB_ENV loading for ALL subsequent steps.
        exported = dict(line.split("=", 1)
                        for line in self.env_file.read_text().splitlines())
        self.assertIn("HELM_PLUGINS", exported)
        directory = Path(exported["HELM_PLUGINS"])
        self.assertTrue(directory.is_dir())
        self.assertEqual(directory.parent, self.runner_temp)
        return {**self.env, **exported}

    def test_fixture_reproduces_duplicate_plugin_failure(self):
        result = self.helm("plugin", "list")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('two plugins claim the name "diff"', result.stderr)

    def test_existing_duplicates_are_ignored_without_deleting_them(self):
        isolated = self.isolate()
        result = self.helm("plugin", "list", env=isolated)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("diff", result.stdout)
        after = {str(p.relative_to(self.home)): p.read_bytes()
                 for p in self.home.rglob("*") if p.is_file()}
        self.assertEqual(self.before, after)

    def test_each_invocation_gets_a_fresh_empty_directory(self):
        first = self.isolate()["HELM_PLUGINS"]
        (Path(first) / "previous-invocation").touch()
        second = self.isolate()["HELM_PLUGINS"]
        self.assertNotEqual(first, second)
        self.assertEqual(list(Path(second).iterdir()), [])
        self.assertTrue((Path(first) / "previous-invocation").is_file())

    def test_isolation_failure_does_not_fall_back_to_shared_plugins(self):
        step = next(s for s in STEPS if s.get("name") == "Isolate Helm plugins")
        broken = {**self.env, "RUNNER_TEMP": str(self.root / "missing")}
        result = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", step["run"]],
                                env=broken, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.env_file.read_text(), "")
        self.assertFalse(step.get("continue-on-error", False))

    def test_isolated_helm_renders_and_still_rejects_invalid_charts(self):
        isolated = self.isolate()
        chart = self.root / "chart"
        (chart / "templates").mkdir(parents=True)
        (chart / "Chart.yaml").write_text(
            "apiVersion: v2\nname: fixture\nversion: 0.1.0\n")
        template = chart / "templates/configmap.yaml"
        template.write_text("apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: fixture\n")
        for command in ("lint", "template"):
            result = self.helm(command, str(chart), env=isolated)
            self.assertEqual(result.returncode, 0, result.stderr)
        template.write_text('{{ fail "render must fail closed" }}\n')
        result = self.helm("template", str(chart), env=isolated)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("render must fail closed", result.stderr)
        gate = next(s for s in STEPS if s.get("name") == "Render every changed helmfile")
        self.assertFalse(gate.get("continue-on-error", False))
        self.assertIn("set -euo pipefail", gate["run"])
        self.assertIn('helmfile --file "$helmfile_path" lint', gate["run"])
        self.assertIn('helmfile --file "$helmfile_path" template', gate["run"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
