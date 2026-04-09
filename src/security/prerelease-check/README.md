<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>prerelease-check</h1></td>
  </tr>
</table>

Composite action that scans dependency files for pre-release version pins (`-beta`, `-rc`) that should not reach production. Checks `go.mod`, `package.json`, and `Dockerfile` for unstable version references and reports findings via GitHub annotations and step summary.

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `scan-ref` | Directory to scan for pre-release versions | No | `.` |
| `app-name` | Application name for reporting context | No | — |

## Outputs

| Output | Description |
|---|---|
| `has-findings` | `true` if pre-release versions were detected |
| `findings-count` | Number of pre-release version findings |

## What it scans

| File | Pattern | Example match |
|---|---|---|
| `go.mod` | `vX.Y.Z-beta.*` / `vX.Y.Z-rc.*` | `v1.2.3-beta.1` |
| `package.json` | `"X.Y.Z-beta.*"` / `"X.Y.Z-rc.*"` | `"2.0.0-rc.1"` |
| `Dockerfile` | `:X.Y.Z-beta.*` / `:X.Y.Z-rc.*` | `golang:1.21.0-beta1` |

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
