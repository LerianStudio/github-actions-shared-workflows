<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>gitops-chart-update</h1></td>
  </tr>
</table>

Pins a newly released Helm chart version into the GitOps repository, gated by render and orphan-key checks.

## Why it exists

`gitops-update.yml` owns the **image tag** in `values.yaml`. Nothing owned the **chart version** in `helmfile.yaml`, so charts drifted while images kept up — by up to two majors. Renovate covered the gap for a while but is now scoped to third-party addons only, which leaves application charts without an owner.

This workflow closes that: the chart repository release calls it once per published chart.

## Architecture

```
chart repo release (LerianStudio/helm)
        ↓  workflow_call
gitops-chart-update.yml            ← orchestration, secrets routing
        ↓  uses:
src/deploy/gitops-chart-update     ← the steps
        ↓  writes
LerianStudio/<name>-gitops
```

Full behaviour — routing table, gates, inputs and outputs — is documented in the composite: [`src/deploy/gitops-chart-update/README.md`](../src/deploy/gitops-chart-update/README.md).

## Inputs

| Input | Description | Required | Default |
|---|---|---|---|
| `chart_name` | Chart name, also the deployment-matrix key | yes | — |
| `chart_version` | The version just published | yes | — |
| `chart_ref` | Full OCI reference | yes | — |
| `gitops_repository` | Target repo; empty uses the `GITOPS_REPOSITORY` org variable | no | `''` |
| `deployment_matrix_ref` | Ref to read the deployment matrix from | no | `main` |
| `envs` | Override the channel-derived env list | no | `''` |
| `fail_on_orphan` | Fail on a key the chart dropped | no | `true` |
| `dry_run` | Resolve and gate without delivering | no | `false` |
| `enable_argocd_sync` | Sync the affected applications and wait for healthy after a direct commit | no | `true` |
| `argocd_sync_timeout` | Seconds to wait for each application to become healthy | no | `600` |

## Outputs

| Output | Description |
|---|---|
| `has_changes` | `true` when at least one pinned version changed |
| `level` | Most restrictive transition across every environment touched |

## Secrets

| Secret | Purpose |
|---|---|
| `GITOPS_APP_ID` / `GITOPS_APP_PRIVATE_KEY` | GitHub App that writes to the GitOps repository |
| `LERIAN_CI_CD_USER_GPG_KEY` / `_PASSWORD` | Commit signing; the target ruleset requires signed commits |
| `LERIAN_CI_CD_USER_NAME` / `_EMAIL` | Committer identity matching the GPG key |
| `ARGOCD_TOKEN` | Only read when `enable_argocd_sync` is true; the server comes from the `ARGOCD_URL` variable |

## Usage

```yaml
# Production — tier channel
jobs:
  notify-gitops:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-chart-update.yml@tier-2
    with:
      chart_name: midaz
      chart_version: 9.1.0
      chart_ref: oci://ghcr.io/lerianstudio/midaz-helm
    secrets: inherit
```

```yaml
# Testing — develop
jobs:
  notify-gitops:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-chart-update.yml@develop
    with:
      chart_name: midaz
      chart_version: 9.1.0
      chart_ref: oci://ghcr.io/lerianstudio/midaz-helm
      dry_run: true
    secrets: inherit
```

## Testing a change

`dry_run: true` resolves the targets and runs both gates, then stops before the GPG import, the commit, the push and the pull request. It prints the resolved plan, the environments left alone because they are pinned to another channel, and the route it would have taken.

```yaml
uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-chart-update.yml@develop
with:
  chart_name: fetcher
  chart_version: 3.2.0
  chart_ref: oci://ghcr.io/lerianstudio/fetcher-helm
  dry_run: true
```
