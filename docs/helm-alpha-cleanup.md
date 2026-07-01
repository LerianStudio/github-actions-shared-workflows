<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>helm-alpha-cleanup</h1></td>
  </tr>
</table>

Reusable workflow that enforces the TTL of alpha Helm chart packages published by [`helm-alpha-release`](./helm-alpha-release.md). It deletes GHCR package versions in the alpha namespace with alpha tags older than a cut-off.

## What it does

Three filters combine (AND) — nothing outside scope is ever deleted:

| Filter | Guards against |
|---|---|
| `image_names: alpha/*` | Deleting a **real release** (different package name → invisible here) |
| `cut_off: 3d` | Deleting an alpha **within its TTL** (fresh alphas stay) |
| `image_tags: *-alpha*` | Deleting anything without an alpha tag |
| `keep_n_most_recent: 5` | Wiping a package entirely |

Manual dispatch defaults to **dry-run** (preview only); the scheduled run deletes for real.

## Inputs

| Input | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `account` | `string` | No | `lerianstudio` | Org/user owning the packages |
| `image_names` | `string` | No | `alpha/*` | Package name globs |
| `image_tags` | `string` | No | `*-alpha*` | Tag globs |
| `cut_off` | `string` | No | `3d` | Age threshold |
| `keep_n_most_recent` | `number` | No | `5` | Minimum versions kept per package |
| `runner_type` | `string` | No | `ubuntu-latest` | Runner label |
| `dry_run` | `boolean` | No | `false` | Preview without applying |

## Secrets

| Secret | Required | Description |
|---|---|---|
| `GHCR_CLEANUP_PAT` | Yes | PAT with `delete:packages` (`GITHUB_TOKEN` cannot delete org-level packages) |

## Usage

### Scheduled caller (per repo)

```yaml
# .github/workflows/helm-alpha-cleanup.yml
name: Helm Alpha Cleanup

on:
  schedule:
    - cron: "0 3 * * *"   # daily, 03:00 UTC
  workflow_dispatch:
    inputs:
      dry_run:
        type: boolean
        default: true

permissions:
  packages: write

jobs:
  cleanup:
    # Testing: pin to @develop. Production: pin to a stable @vX.Y.Z.
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/helm-alpha-cleanup.yml@v1
    with:
      # schedule deletes for real; manual dispatch previews unless you flip dry_run
      dry_run: ${{ github.event_name == 'workflow_dispatch' && inputs.dry_run || false }}
    secrets:
      GHCR_CLEANUP_PAT: ${{ secrets.GHCR_CLEANUP_PAT }}
```

## Permissions required

```yaml
permissions:
  packages: write
```
