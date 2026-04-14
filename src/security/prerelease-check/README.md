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

## Outputs

| Output | Description |
|---|---|
| `has-findings` | `true` if unstable versions were detected |
| `findings-count` | Number of unstable version findings |
| `artifact-file` | Path to the JSON findings file for consumption by `pr-security-reporter` |

## What it scans

For `go.mod` and `package.json`: matches any semver with a pre-release suffix starting with a letter (`x.y.z-<letter...>`). For `Dockerfile`: only matches known pre-release prefixes to avoid false positives on stable image variants.

| File | Scanned patterns | Blocked (unstable) | Allowed (stable) |
|---|---|---|---|
| `go.mod` | `vX.Y.Z-<letter...>` | `v1.2.3-beta.1`, `v1.2.3-rc.1`, `v1.2.3-alpha.1` | `v1.2.3`, `v0.0.0-20240101-abcdef012345` |
| `package.json` | `"[~^>=]*X.Y.Z-<letter...>"` | `"^2.0.0-beta.1"`, `"~1.0.0-rc.3"` | `"2.0.0"` |
| `Dockerfile`, `*.dockerfile`, `Dockerfile.*` | `:X.Y.Z-(alpha\|beta\|rc\|dev\|...)` | `golang:1.21.0-beta1` | `golang:1.21.0`, `python:3.12-slim`, `node:20-alpine` |

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
