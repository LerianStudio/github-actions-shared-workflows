<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>trivy-image-scan</h1></td>
  </tr>
</table>

Composite action that runs Trivy vulnerability and license scans on a Docker image. Produces human-readable table output and machine-readable artifacts (SARIF and JSON) for downstream consumption by [`pr-security-reporter`](../pr-security-reporter/).

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `image-ref` | Docker image reference to scan (e.g., `org/app:tag`) | Yes | — |
| `app-name` | Application name — used for artifact file naming | Yes | — |
| `severity-table` | Severity levels to show in table output | No | `CRITICAL,HIGH` |
| `severity-sarif` | Severity levels to capture in SARIF artifact | No | `UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL` |
| `ignore-unfixed` | Only report vulnerabilities with available fixes | No | `true` |
| `vuln-type` | Vulnerability types to scan for (comma-separated) | No | `os,library` |
| `enable-license-scan` | Run license compliance scan and produce JSON artifact | No | `false` |
| `trivy-version` | Trivy version to install | No | `v0.69.3` |

## Outputs

| Output | Description |
|---|---|
| `vuln-scan-sarif` | File path of the vulnerability scan SARIF artifact |
| `license-scan-json` | File path of the license scan JSON artifact (empty if license scan disabled) |

## Artifact naming convention

This composite produces the following files in the runner working directory:

| File | Format | Condition | Purpose |
|---|---|---|---|
| `trivy-vulnerability-scan-docker-<app-name>.sarif` | SARIF | Always | Vulnerability results for `pr-security-reporter` and GitHub Security tab |
| `trivy-license-scan-docker-<app-name>.json` | JSON | `enable-license-scan: true` | License results for health score compliance |

## Usage

### As a composite step (within a security workflow job)

```yaml
jobs:
  security:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - uses: actions/checkout@v6
      - uses: docker/setup-buildx-action@v4

      - name: Build Docker Image
        uses: docker/build-push-action@v7
        with:
          load: true
          push: false
          tags: myorg/myapp:scan

      - name: Trivy Image Scan
        uses: LerianStudio/github-actions-shared-workflows/src/security/trivy-image-scan@develop
        with:
          image-ref: 'myorg/myapp:scan'
          app-name: 'my-service'
          enable-license-scan: 'true'
```

### Production usage

```yaml
- uses: LerianStudio/github-actions-shared-workflows/src/security/trivy-image-scan@v1.0.0
  with:
    image-ref: 'myorg/myapp:scan'
    app-name: my-service
```

## Permissions required

```yaml
permissions:
  contents: read
  security-events: write  # only if uploading SARIF to GitHub Security tab
```
