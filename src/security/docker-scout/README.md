<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>docker-scout</h1></td>
  </tr>
</table>

Composite action that runs [Docker Scout](https://docs.docker.com/scout/) analysis on a locally built Docker image, producing a quickview summary and detailed CVE report. Optionally exports results in SARIF format.

Uses [`docker/scout-action@v1.20.2`](https://github.com/docker/scout-action) — chosen for being the official Docker Scout integration maintained by Docker Inc.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `image` | Image reference to scan (local tag) | Yes | — |
| `dockerhub-user` | DockerHub username for Scout authentication | Yes | — |
| `dockerhub-password` | DockerHub password for Scout authentication | Yes | — |
| `github-token` | GitHub token | No | `${{ github.token }}` |
| `only-severities` | Severities to include (csv) | No | `critical,high,medium,low` |
| `exit-code` | Fail the step if vulnerabilities are found | No | `false` |
| `write-comment` | Post results as a PR comment (via Scout) | No | `false` |
| `sarif-file` | Path to export SARIF file (empty = skip) | No | `""` |
| `enable-recommendations` | Run Scout recommendations (non-root user, attestation gaps, base image issues) | No | `true` |

## Outputs

| Output | Description |
|--------|-------------|
| `quickview` | Markdown summary from Scout quickview |
| `cves` | Markdown CVE details from Scout cves |
| `has-vulnerabilities` | `true` if vulnerabilities were found |
| `recommendations` | Raw recommendations output (Dockerfile issues, attestation gaps, non-root user) |

## Usage as composite step

```yaml
jobs:
  scan:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Build image
        uses: docker/build-push-action@v7
        with:
          load: true
          push: false
          tags: myorg/myapp:scan

      - name: Docker Scout Analysis
        id: scout
        uses: ./src/security/docker-scout
        with:
          image: myorg/myapp:scan
          dockerhub-user: ${{ secrets.DOCKER_USERNAME }}
          dockerhub-password: ${{ secrets.DOCKER_PASSWORD }}
          only-severities: critical,high
```

## Usage via reusable workflow

```yaml
jobs:
  security-scan:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-security-scan.yml@v1.0.0
    with:
      enable_docker_scout: true
    secrets: inherit
```

## Required permissions

```yaml
permissions:
  contents: read
  pull-requests: write   # only if write-comment is true
```

## Prerequisites

Docker Scout requires a Docker Hub account with Scout access. Ensure the `DOCKER_USERNAME` and `DOCKER_PASSWORD` secrets correspond to an account with an active Docker Scout subscription (Free, Team, or Business).
