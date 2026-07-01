<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>helm-alpha-publish</h1></td>
  </tr>
</table>

Composite action that packages a Helm chart as a **disposable alpha prerelease** and pushes it to an isolated OCI namespace (default `oci://ghcr.io/lerianstudio/alpha`). The alpha version is `<chart-version>-alpha.<UTC-timestamp>.<short-sha>`. Isolating alphas in their own namespace lets the retention job prune them without ever touching real releases.

Does **not** run semantic-release: no `Chart.yaml` commit, git tag, CHANGELOG, back-merge or notifications.

Depends on [`azure/setup-helm`](https://github.com/Azure/setup-helm) to install the `helm` CLI on the runner — required for `helm dependency update`, `helm lint`, `helm package`, and `helm push` to the OCI registry. It is the maintained, official installer, avoiding a hand-rolled download/verify step.

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `chart` | Chart directory name under `charts-path` | Yes | — |
| `charts-path` | Path to the charts directory | No | `charts` |
| `registry` | OCI registry/namespace to push to | No | `oci://ghcr.io/lerianstudio/alpha` |
| `registry-host` | Registry host for `helm registry login` | No | `ghcr.io` |
| `registry-username` | Username for registry login | No | `lerianstudio` |
| `registry-password` | Token with `packages:write` | Yes | — |
| `dry-run` | Package and validate but do not push | No | `false` |

## Outputs

| Output | Description |
|---|---|
| `version` | Generated alpha version |
| `reference` | Full OCI reference of the pushed chart |

## Usage

### As a composite action

```yaml
jobs:
  alpha:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: LerianStudio/github-actions-shared-workflows/src/build/helm-alpha-publish@v1
        with:
          chart: flowker
          registry-password: ${{ secrets.GITHUB_TOKEN }}
```

### As a reusable workflow (recommended)

```yaml
jobs:
  alpha:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/helm-alpha-release.yml@v1
    with:
      chart: flowker
    secrets: inherit
```

## Permissions required

```yaml
permissions:
  contents: read
  packages: write
```
