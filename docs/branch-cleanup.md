# branch-cleanup

Reusable workflow that keeps repositories clean by automatically deleting stale branches and removing branches after PR merges.

## What it does

| Mode | Trigger | Behavior |
|---|---|---|
| **Stale cleanup** | Schedule / manual dispatch / `workflow_call` | Scans all branches, deletes those with no commits for N days and no open PRs |
| **Merged branch** | `workflow_call` with `merged_branch` input | Deletes the specified branch after a PR merge |

Protected branches (`main`, `master`, `develop`, `release/*`, `hotfix/*`) and branches with GitHub branch protection rules are never deleted.

## Inputs

| Input | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `stale_days` | `number` | No | `30` | Days without commits before a branch is stale |
| `dry_run` | `boolean` | No | `false` | Preview deletions without applying them |
| `protected_branches` | `string` | No | `main,master,develop,release/*,hotfix/*` | Comma-separated patterns to never delete |
| `merged_branch` | `string` | No | `""` | Branch to delete (enables merged mode) |

## Secrets

| Secret | Required | Description |
|---|---|---|
| `GITHUB_TOKEN` | No | Defaults to the automatic token; needs `contents:write` and `pull-requests:read` |

## Usage

### Scheduled stale branch cleanup

```yaml
# .github/workflows/branch-cleanup.yml
name: Branch Cleanup

on:
  schedule:
    - cron: "0 6 * * 1"   # Every Monday at 06:00 UTC
  workflow_dispatch:
    inputs:
      dry_run:
        type: boolean
        default: false

jobs:
  cleanup:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/branch-cleanup.yml@v1.0.0
    with:
      stale_days: 30
      dry_run: ${{ inputs.dry_run || false }}
    secrets: inherit
```

### Delete branch on PR merge

```yaml
# .github/workflows/delete-merged-branch.yml
name: Delete Merged Branch

on:
  pull_request:
    types: [closed]

jobs:
  cleanup:
    if: ${{ github.event.pull_request.merged }}
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/branch-cleanup.yml@v1.0.0
    with:
      merged_branch: ${{ github.head_ref }}
    secrets: inherit
```

### Both in a single caller file

```yaml
name: Branch Cleanup

on:
  schedule:
    - cron: "0 6 * * 1"
  pull_request:
    types: [closed]
  workflow_dispatch:
    inputs:
      dry_run:
        type: boolean
        default: false

jobs:
  stale:
    if: ${{ github.event_name != 'pull_request' }}
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/branch-cleanup.yml@v1.0.0
    with:
      stale_days: 30
      dry_run: ${{ inputs.dry_run || false }}
    secrets: inherit

  merged:
    if: ${{ github.event_name == 'pull_request' && github.event.pull_request.merged }}
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/branch-cleanup.yml@v1.0.0
    with:
      merged_branch: ${{ github.head_ref }}
    secrets: inherit
```

## Permissions

```yaml
permissions:
  contents: write
  pull-requests: read
```
