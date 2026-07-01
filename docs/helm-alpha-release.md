<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>helm-alpha-release</h1></td>
  </tr>
</table>

Reusable workflow that publishes a **disposable alpha prerelease** of a Helm chart to an isolated OCI namespace, for testing a chart before it is released through the normal `develop`/`main` pipeline. Alphas have a short TTL enforced by [`helm-alpha-cleanup`](./helm-alpha-cleanup.md).

## What it does

| Step | Behavior |
|---|---|
| Resolve version | `<chart-version>-alpha.<UTC-timestamp>.<short-sha>` from the checked-out ref |
| Validate | `helm dependency update` + `helm lint`; fails with the chart list if `chart` is not found |
| Publish | `helm package` + `helm push` to `registry` (default `oci://ghcr.io/lerianstudio/alpha`) |

Because the checkout uses the caller's ref, **a chart that only exists on a work branch is published as long as the workflow is dispatched from that branch**. It does **not** touch git history, CHANGELOG, tags or notifications.

## Inputs

| Input | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `chart` | `string` | Yes | — | Chart directory name under `charts_path` |
| `charts_path` | `string` | No | `charts` | Path to the charts directory |
| `registry` | `string` | No | `oci://ghcr.io/lerianstudio/alpha` | OCI namespace to push to |
| `registry_host` | `string` | No | `ghcr.io` | Registry host for login |
| `registry_username` | `string` | No | `lerianstudio` | Registry login user |
| `runner_type` | `string` | No | `ubuntu-latest` | Runner label |
| `dry_run` | `boolean` | No | `false` | Package/validate but do not push |

## Secrets

| Secret | Required | Description |
|---|---|---|
| `REGISTRY_PASSWORD` | No | Token with `packages:write`. Falls back to `GITHUB_TOKEN` when omitted. |

## Usage

### Manual dispatch caller (per repo)

```yaml
# .github/workflows/helm-alpha.yml
name: Helm Alpha Release

on:
  workflow_dispatch:
    inputs:
      chart:
        description: "Chart (dir under charts/) — may be a new chart on your branch"
        required: true
        type: string
      dry_run:
        type: boolean
        default: false

permissions:
  contents: read
  packages: write

jobs:
  alpha:
    # Testing: pin to @develop. Production: pin to a stable @vX.Y.Z.
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/helm-alpha-release.yml@v1
    with:
      chart: ${{ inputs.chart }}
      dry_run: ${{ inputs.dry_run }}
    secrets: inherit
```

> Dispatch from your work branch (the branch selector in **Run workflow**) so the checkout uses that ref and picks up new charts.

## Permissions required

```yaml
permissions:
  contents: read
  packages: write
```
