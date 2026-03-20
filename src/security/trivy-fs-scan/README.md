<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>trivy-fs-scan</h1></td>
  </tr>
</table>

Composite action that runs Trivy filesystem scans for secrets and vulnerabilities. Produces human-readable table output (with configurable fail behavior) and machine-readable artifacts (SARIF and JSON) for downstream consumption by [`pr-security-reporter`](../pr-security-reporter/).

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `scan-ref` | Path to scan (e.g., `.` for repo root or a component directory) | No | `.` |
| `app-name` | Application name — used for artifact file naming | Yes | — |
| `skip-dirs` | Comma-separated directories to skip during scanning | No | `.git,node_modules,dist,build,.next,coverage,vendor` |
| `trivy-version` | Trivy version to install | No | `v0.69.3` |
| `exit-code-secret-scan` | Exit code when secrets are found in table output (`1` to fail, `0` to warn only) | No | `1` |

## Outputs

| Output | Description |
|---|---|
| `secret-scan-sarif` | File path of the secret scan SARIF artifact |
| `fs-vuln-json` | File path of the filesystem vulnerability JSON artifact |

## Artifact naming convention

This composite produces the following files in the runner working directory:

| File | Format | Purpose |
|---|---|---|
| `trivy-secret-scan-<app-name>.sarif` | SARIF | Secret scan results for GitHub Security tab upload |
| `trivy-fs-vuln-<app-name>.json` | JSON | Filesystem vulnerability results for `pr-security-reporter` |

## Usage

### As a composite step (within a security workflow job)

```yaml
jobs:
  security:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - uses: actions/checkout@v6

      - name: Trivy Filesystem Scan
        id: fs-scan
        uses: LerianStudio/github-actions-shared-workflows/src/security/trivy-fs-scan@v1.x.x
        with:
          scan-ref: '.'
          app-name: 'my-service'
```

### Monorepo usage (scan a specific component)

```yaml
- name: Trivy Filesystem Scan
  uses: LerianStudio/github-actions-shared-workflows/src/security/trivy-fs-scan@v1.x.x
  with:
    scan-ref: ${{ matrix.working_dir }}
    app-name: ${{ matrix.name }}
```

### Production usage

```yaml
- uses: LerianStudio/github-actions-shared-workflows/src/security/trivy-fs-scan@v1.0.0
  with:
    app-name: my-service
```

## Permissions required

```yaml
permissions:
  contents: read
  security-events: write  # only if uploading SARIF to GitHub Security tab
```
