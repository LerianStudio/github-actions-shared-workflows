<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>prerelease-check</h1></td>
  </tr>
</table>

Composite action that scans dependency files for unstable version pins. Only stable semver (`x.y.z`) and SHA-based pins (including Go pseudo-versions) are allowed. Checks `go.mod`, `package.json`, and `Dockerfile` and reports findings via GitHub annotations and step summary.

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `scan-ref` | Directory to scan for pre-release versions | No | `.` |
| `app-name` | Application name for reporting context | No | `''` |
| `target-branch` | PR target branch (e.g. `github.base_ref`). Selects the annotation level (see below). Empty = warning | No | `''` |
| `block-branches` | Comma-separated branches where pre-release pins annotate as error. Must match the downstream gate | No | `release-candidate,main` |
| `allow-file` | Path (relative to each scanned base) to a file of accepted pre-release pins. Matching findings are exempted (reported as `::notice::`). Absent file = no exemptions | No | `.prerelease-allow` |
| `prerelease-pattern` | Override the semver pre-release regex (applied to `go.mod`, `package.json` and `Dockerfile`). Wire from an org/repo variable to tune the policy without a release. Empty = built-in allowlist | No | `''` |

## Outputs

| Output | Description |
|---|---|
| `has-findings` | `true` if unstable versions were detected |
| `findings-count` | Number of unstable version findings |
| `artifact-file` | Path to the JSON findings file for consumption by `pr-security-reporter` |

## Annotation level

This action never fails the job itself — it only reports. The summary annotation level mirrors the branch policy so it does not contradict a downstream branch-aware gate: when `target-branch` is one of `block-branches`, findings annotate as `::error::`; otherwise (including an empty/unknown `target-branch`) they annotate as `::warning::`. Per-finding line annotations are always warnings. Enforcement (`exit 1`) belongs to the consuming workflow's gate, not to this action.

## What it scans

For all file types, only known pre-release keywords (`alpha`, `beta`, `rc`, `dev`, `preview`, `canary`, `snapshot`, `nightly`) are matched. This allowlist avoids false positives on stable vendor-suffixed releases (e.g. the `-vault-N` suffix, such as `v1.0.1-vault-7`) and stable image variants (e.g. `-slim`, `-alpine`, `-bookworm`).

| File | Scanned patterns | Blocked (unstable) | Allowed (stable) |
|---|---|---|---|
| `go.mod` | `vX.Y.Z-(alpha\|beta\|rc\|dev\|...)` | `v1.2.3-beta.1`, `v1.2.3-rc.1`, `v1.2.3-alpha.1` | `v1.2.3`, `v1.0.1-vault-7`, `v0.0.0-20240101120000-abcdef012345` |
| `package.json` | `"[~^<>=]*X.Y.Z-(alpha\|beta\|rc\|dev\|...)"` | `"^2.0.0-beta.1"`, `"~1.0.0-rc.3"`, `"<2.0.0-beta.1"` | `"2.0.0"` |
| `Dockerfile`, `*.dockerfile`, `Dockerfile.*` | `:X.Y.Z-(alpha\|beta\|rc\|dev\|...)` | `golang:1.21.0-beta1` | `golang:1.21.0`, `python:3.12-slim`, `node:20-alpine` |

## Overriding the pattern

The regex is fixed in the action but overridable through the `prerelease-pattern` input, wired from an organization (or repository) variable so the policy can be tuned centrally without cutting a new release. The `pr-security-scan` reusable workflow already forwards `${{ vars.PRERELEASE_PATTERN }}`; define that variable once at the org level to apply it across every consuming repo.

- Set it in **Settings → Secrets and variables → Actions → Variables** (organization scope) with a value such as `[0-9]+\.[0-9]+\.[0-9]+-(alpha|beta|rc|dev|preview|canary|snapshot|nightly)`.
- Leaving the variable undefined (the default) falls back to the built-in allowlist above — behavior is unchanged for repos that never set it.
- The same override applies to `go.mod`, `package.json` and `Dockerfile` scanning.

> **Security — this is a global policy knob.** Because the variable is read at org scope, anyone able to edit org variables can loosen (or tighten) the pre-release gate for **every** repository at once. Restrict who can manage Actions variables and prefer the per-pin `.prerelease-allow` allow-file for narrow, reviewable exemptions.

## Allowlisting accepted pins

Some pre-release pins cannot be remediated by upgrade — a direct dependency whose upstream ships no stable release (only `beta`/`rc`), or a pre-release version reached transitively through a dependency you do not control. For these, list the accepted entries in an allow-file (default `.prerelease-allow`, resolved relative to each scanned base — the `scan-ref` directory and the repository root — so a monorepo component can carry its own). Matching findings are exempted and reported as `::notice::` instead of blocking — the same discipline `.trivyignore` applies to CVEs with no fixed version. Any pin **not** listed still blocks.

```text
# .prerelease-allow — one accepted entry per line; '#' comments and blank lines ignored.
# go-imap v2 has no stable upstream release (v2 is beta-only). Direct dep.
# Review by: 2026-09-30
github.com/emersion/go-imap/v2 v2.0.0-beta.8

# sindarian-ui ships no stable v2 yet. Copied verbatim from package.json,
# quotes and trailing comma included.
"@lerianstudio/sindarian-ui": "2.0.0-beta.6",
```

Matching is on the **first two whitespace-delimited tokens of the raw scanned line**, and an entry is compared to them **verbatim — the only processing applied to it is `#` comment stripping and whitespace trimming**. Nothing else is removed: quotes, colons, commas and version range operators are all part of the key.

| Finding in | Raw line in the file | Entry to write |
|---|---|---|
| `go.mod` | tab-indented, `github.com/emersion/go-imap/v2 v2.0.0-beta.8 // indirect` | `github.com/emersion/go-imap/v2 v2.0.0-beta.8` |
| `package.json` | indented, `"@lerianstudio/sindarian-ui": "2.0.0-beta.6",` | `"@lerianstudio/sindarian-ui": "2.0.0-beta.6",` |
| `Dockerfile` | `FROM node:20.0.0-rc1 AS builder` | `FROM node:20.0.0-rc1` |

Leading indentation and a trailing `// indirect` never affect the match, because only the first two tokens are compared. A leading `require` keyword, and the whitespace following it (the `go.mod` single-line form), is stripped too, so both `go.mod` spellings key the same. Everything after the second token is ignored, so the `package.json` entry must carry the trailing comma when the line in the file has one, and the `Dockerfile` entry stops at the tag.

> **Compatibility.** Until this was fixed, allow-file entries were put through shell word splitting, which stripped the quotes and made every `package.json` entry inert unless its quotes were backslash-escaped (`\"pkg\": \"2.0.0-beta.6\",`). Repositories that worked around it that way keep working: a backslash before a quote is still dropped. New entries should be written unescaped, exactly as the line appears in the file.

> **Security — review your exemptions.** The allow-file is read from the scanned working tree, so — exactly like `.trivyignore` — a PR can add its own entry and self-exempt a pin. Put `.prerelease-allow` under `CODEOWNERS` in consuming repos so every exemption gets a dedicated review rather than being self-approved.

## Usage

### As a composite step (within a security workflow job)

```yaml
jobs:
  security:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - uses: actions/checkout@v6

      - name: Pre-release Version Check
        id: prerelease-check
        uses: LerianStudio/github-actions-shared-workflows/src/security/prerelease-check@v1.x.x
        with:
          scan-ref: '.'
          app-name: 'my-app'

      - name: Fail on pre-release versions
        if: steps.prerelease-check.outputs.has-findings == 'true'
        run: exit 1
```

### Via the reusable workflow

Pre-release checks are built into the `pr-security-scan` workflow and enabled by default:

```yaml
jobs:
  security-scan:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-security-scan.yml@v1.x.x
    with:
      enable_prerelease_check: true   # default
    secrets: inherit
```

## Permissions required

```yaml
permissions:
  contents: read
```
