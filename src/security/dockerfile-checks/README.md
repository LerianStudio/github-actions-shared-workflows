<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>dockerfile-checks</h1></td>
  </tr>
</table>

Composite action that runs Docker Hub Health Score compliance checks on a Dockerfile. Verifies non-root user configuration and downloads the CISA Known Exploited Vulnerabilities (KEV) catalog for cross-referencing by [`pr-security-reporter`](../pr-security-reporter/).

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `dockerfile-path` | Path to the Dockerfile to check | Yes | — |

## Outputs

| Output | Description |
|---|---|
| `has-non-root-user` | `true` if the Dockerfile sets a non-root `USER` directive, `false` otherwise |
| `cisa-kev-path` | File path of the downloaded CISA KEV catalog |

## Artifact naming convention

This composite produces the following file in the runner working directory:

| File | Format | Purpose |
|---|---|---|
| `cisa-kev.json` | JSON | CISA KEV catalog for cross-referencing CVEs in `pr-security-reporter` |

## Usage

### As a composite step (within a security workflow job)

```yaml
jobs:
  security:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - uses: actions/checkout@v6

      - name: Dockerfile Compliance Checks
        id: dockerfile-checks
        uses: LerianStudio/github-actions-shared-workflows/src/security/dockerfile-checks@v1.x.x
        with:
          dockerfile-path: './Dockerfile'

      - name: Use results
        run: |
          echo "Non-root user: ${{ steps.dockerfile-checks.outputs.has-non-root-user }}"
          echo "KEV catalog: ${{ steps.dockerfile-checks.outputs.cisa-kev-path }}"
```

### Production usage

```yaml
- uses: LerianStudio/github-actions-shared-workflows/src/security/dockerfile-checks@v1.0.0
  with:
    dockerfile-path: './Dockerfile'
```

## Permissions required

```yaml
permissions:
  contents: read
```
