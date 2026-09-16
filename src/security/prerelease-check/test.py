#!/usr/bin/env python3

"""Behavioural tests for the `prerelease-check` allow-file.

The composite's scan step is extracted from `action.yml` and run for real
against a throwaway workspace, so these tests exercise the shipped shell rather
than a Python re-implementation of it. No network, no token — only `bash`,
`grep`, `awk`, `sed` and `jq`, all of which the runner image already has.

The allow-file contract under test: an entry is compared **verbatim** against
the first two whitespace-delimited tokens of the raw scanned line. The entry is
therefore only whitespace-trimmed (plus `#` comment stripping) — it is never
put through shell word splitting, which would remove the quotes a
`package.json` finding carries and make every quoted entry silently inert.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ACTION_PATH = REPO_ROOT / "src" / "security" / "prerelease-check" / "action.yml"
README_PATH = REPO_ROOT / "src" / "security" / "prerelease-check" / "README.md"

ACTION = ACTION_PATH.read_text(encoding="utf-8")
README = README_PATH.read_text(encoding="utf-8")

SCAN_STEP = "Scan for pre-release versions"


def _modern_bash():
    """The composite uses arrays; macOS /bin/bash is 3.2, so prefer a bash 4+."""
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


SCAN_SCRIPT = extract_run_body(ACTION, SCAN_STEP)


PACKAGE_JSON = """{
  "name": "example",
  "dependencies": {
    "@lerianstudio/sindarian-ui": "2.0.0-beta.6",
    "react": "19.0.0"
  }
}
"""

# The raw line the scanner reports for the pin above, as it appears in the file.
PACKAGE_JSON_PIN = '"@lerianstudio/sindarian-ui": "2.0.0-beta.6",'

GO_MOD = """module github.com/LerianStudio/example

go 1.23

require (
\tgithub.com/emersion/go-imap/v2 v2.0.0-beta.8 // indirect
\tgithub.com/stretchr/testify v1.9.0
)
"""

GO_MOD_PIN = "github.com/emersion/go-imap/v2 v2.0.0-beta.8"


class ScanRunner:
    """Runs the extracted scan step against a throwaway workspace."""

    def __init__(self, testcase):
        self.dir = Path(tempfile.mkdtemp(prefix="prerelease-check-"))
        testcase.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def write(self, name, content):
        target = self.dir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def run(self, **env_overrides):
        outputs = self.dir / "github_output"
        summary = self.dir / "github_step_summary"
        outputs.touch()
        summary.touch()

        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(self.dir),
            "GITHUB_OUTPUT": str(outputs),
            "GITHUB_STEP_SUMMARY": str(summary),
            "RUNNER_TEMP": str(self.dir),
            "SCAN_DIR": ".",
            "APP_NAME": "",
            "TARGET_BRANCH": "",
            "BLOCK_BRANCHES": "release-candidate,main",
            "ALLOW_FILE": ".prerelease-allow",
            "PRERELEASE_PATTERN": "",
        }
        env.update(env_overrides)

        result = subprocess.run(
            [BASH, "-c", SCAN_SCRIPT],
            cwd=self.dir, env=env, capture_output=True, text=True,
        )
        result.github_output = outputs.read_text(encoding="utf-8")
        result.step_summary = summary.read_text(encoding="utf-8")
        return result

    @staticmethod
    def findings_count(result):
        for line in result.github_output.splitlines():
            if line.startswith("findings_count="):
                return int(line.split("=", 1)[1])
        raise AssertionError(f"findings_count not emitted:\n{result.github_output}")


@unittest.skipUnless(BASH, "requires bash 4+ for the composite's arrays")
class AllowFileTests(unittest.TestCase):
    def setUp(self):
        self.runner = ScanRunner(self)

    def _debug(self, result):
        return f"\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"

    # ----------------- package.json: the documented, quoted form -----------------

    def test_package_json_pin_is_a_finding_without_an_allow_file(self):
        """Control: the pin blocks when nothing exempts it."""
        self.runner.write("package.json", PACKAGE_JSON)
        result = self.runner.run()
        self.assertEqual(self.runner.findings_count(result), 1, self._debug(result))

    def test_quoted_allow_entry_exempts_a_package_json_pin(self):
        """A quoted entry, copied verbatim as the README documents, must match.

        Regression: the entry was trimmed with `xargs`, which performs shell
        quote removal, so `"pkg": "2.0.0-beta.6",` became `pkg: 2.0.0-beta.6,`
        and never equalled the key computed from the quoted scanned line. Every
        quoted exemption was silently inert and the pin kept blocking.
        """
        self.runner.write("package.json", PACKAGE_JSON)
        self.runner.write(".prerelease-allow", PACKAGE_JSON_PIN + "\n")
        result = self.runner.run()
        self.assertEqual(self.runner.findings_count(result), 0, self._debug(result))
        self.assertIn("::notice::Accepted pre-release pin", result.stdout)
        self.assertIn(PACKAGE_JSON_PIN, result.stdout)

    def test_quoted_allow_entry_survives_surrounding_whitespace_and_comments(self):
        """Whitespace and a trailing `#` comment are stripped; quotes are not."""
        self.runner.write("package.json", PACKAGE_JSON)
        self.runner.write(
            ".prerelease-allow",
            "# sindarian-ui ships no stable v2 yet. Review by: 2026-12-31\n"
            "\n"
            f"   {PACKAGE_JSON_PIN}\t  # direct dep, beta-only upstream\n",
        )
        result = self.runner.run()
        self.assertEqual(self.runner.findings_count(result), 0, self._debug(result))

    def test_backslash_escaped_quotes_are_tolerated(self):
        """The workaround form written against the old behaviour keeps working.

        Before the fix, `xargs` turned `\\"pkg\\"` into `"pkg"`, so repositories
        that discovered the bug wrote their entries escaped. Stripping a
        backslash before a quote keeps those allow-files matching.
        """
        self.runner.write("package.json", PACKAGE_JSON)
        escaped = PACKAGE_JSON_PIN.replace('"', '\\"')
        self.runner.write(".prerelease-allow", escaped + "\n")
        result = self.runner.run()
        self.assertEqual(self.runner.findings_count(result), 0, self._debug(result))

    # ----------------- go.mod: unchanged behaviour -----------------

    def test_go_mod_entry_still_matches(self):
        """The unquoted go.mod form worked before the fix and must keep working."""
        self.runner.write("go.mod", GO_MOD)
        self.runner.write(".prerelease-allow", GO_MOD_PIN + "\n")
        result = self.runner.run()
        self.assertEqual(self.runner.findings_count(result), 0, self._debug(result))
        self.assertIn(f"::notice::Accepted pre-release pin (allow-file): {GO_MOD_PIN}", result.stdout)

    def test_go_mod_require_prefixed_entry_still_matches(self):
        """The single-line `require <module> <version>` form keys the same."""
        self.runner.write("go.mod", GO_MOD)
        self.runner.write(".prerelease-allow", f"require {GO_MOD_PIN}\n")
        result = self.runner.run()
        self.assertEqual(self.runner.findings_count(result), 0, self._debug(result))

    # ----------------- negative: an unlisted pin still blocks -----------------

    def test_unlisted_pin_still_blocks(self):
        """Exempting one pin must not exempt its neighbours."""
        self.runner.write("package.json", PACKAGE_JSON)
        self.runner.write("go.mod", GO_MOD)
        self.runner.write(".prerelease-allow", PACKAGE_JSON_PIN + "\n")
        result = self.runner.run(TARGET_BRANCH="main")
        self.assertEqual(self.runner.findings_count(result), 1, self._debug(result))
        self.assertIn("go.mod", result.step_summary)
        self.assertNotIn("package.json", result.step_summary)
        self.assertIn("::error::Found 1 unstable version pin(s)", result.stdout)

    def test_a_different_version_of_an_allowed_module_still_blocks(self):
        """The version is part of the key — an exemption does not cover a bump."""
        self.runner.write("package.json", PACKAGE_JSON)
        self.runner.write(
            ".prerelease-allow",
            '"@lerianstudio/sindarian-ui": "2.0.0-beta.5",\n',
        )
        result = self.runner.run()
        self.assertEqual(self.runner.findings_count(result), 1, self._debug(result))


class DocumentationTests(unittest.TestCase):
    """The README is the only place the entry format is specified."""

    def test_readme_shows_the_quoted_package_json_entry_verbatim(self):
        self.assertIn(PACKAGE_JSON_PIN, README, "README must show a quoted package.json entry")

    def test_readme_states_that_only_whitespace_is_trimmed(self):
        self.assertIn("whitespace trimming", README, "README must say entries are only whitespace-trimmed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
