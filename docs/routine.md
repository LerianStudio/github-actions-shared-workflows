<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>routine</h1></td>
  </tr>
</table>

Reusable workflow that orchestrates standard repository maintenance routines: branch cleanup (stale and post-merge), stale PR/issue triage, label synchronization, and workflow runs cleanup.

This is an aggregator — it does not contain logic itself, but dispatches to the underlying reusable workflows based on the caller event and the `routine` input. Use it as the single integration point in consumer repositories instead of wiring each routine workflow individually.

## What it does

| Job | Triggered when | Calls |
|---|---|---|
| `branch_cleanup_merged` | `pull_request` closed and merged | `branch-cleanup.yml` (merged mode, `dry_run: false`) |
| `branch_cleanup_stale` | `schedule` or dispatch with `routine: all\|branch-cleanup-stale` | `branch-cleanup.yml` (stale mode) |
| `stale_pr` | `schedule` or dispatch with `routine: all\|stale-pr` | `stale-pr.yml` |
| `stale_issue` | `schedule` or dispatch with `routine: all\|stale-issue` | `stale-issue.yml` |
| `labels_sync` | `push`, `schedule`, or dispatch with `routine: all\|labels-sync` | `labels-sync.yml` |
| `workflow_runs_cleanup` | `schedule` or dispatch with `routine: all\|workflow-runs-cleanup` | `workflow-runs-cleanup.yml` |

The caller controls the triggers (schedule cron, push paths, pull_request types, workflow_dispatch inputs). `routine.yml` decides which jobs run based on `github.event_name` and the `routine` input.

## Inputs

| Input | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `routine` | `string` | No | `all` | Routine to run: `all`, `branch-cleanup-stale`, `stale-pr`, `stale-issue`, `labels-sync`, `workflow-runs-cleanup` |
| `dry_run` | `boolean` | No | `false` | Preview changes without applying them |
| `merged_branch` | `string` | No | `""` | Branch to delete in merged-PR mode — typically `${{ github.head_ref }}` |
| `branch_stale_days` | `number` | No | `20` | Days without commits before a branch is stale |
| `pr_days_before_stale` | `number` | No | `20` | Days of PR inactivity before the stale label is applied |
| `pr_days_before_close` | `number` | No | `7` | Days after a PR is marked stale before it is closed |
| `pr_operations_per_run` | `number` | No | `60` | Maximum API operations per stale PR run (non-schedule events) |
| `pr_operations_per_run_schedule` | `number` | No | `420` | Maximum API operations per stale PR run on `schedule` |
| `issue_days_before_stale` | `number` | No | `30` | Days of issue inactivity before the stale label is applied |
| `issue_days_before_close` | `number` | No | `7` | Days after an issue is marked stale before it is closed |
| `workflow_runs_retention_days` | `number` | No | `45` | Delete workflow runs older than this many days |
| `protected_branches` | `string` | No | `main,master,develop,release-candidate,hotfix/*` | Branch patterns the cleanup never deletes — full override |
| `extra_protected_branches` | `string` | No | `""` | Branch patterns appended to `protected_branches` (use this when you only want to add patterns) |

## Secrets

Pass `secrets: inherit` from the caller. Underlying workflows use:

| Secret | Required | Description |
|---|---|---|
| `GITHUB_TOKEN` | No | Auto-injected; covers branch cleanup, label sync, workflow runs cleanup |
| `MANAGE_TOKEN` | No | Preferred for stale PR/issue scans so the bot identity attributes the labels and comments. Falls back to `GITHUB_TOKEN` when absent. |

## Permissions

```yaml
permissions:
  contents: write
  pull-requests: write
  issues: write
  actions: write
```

## Usage

### Standard caller — full routine setup

Drop this in any consumer repository as `.github/workflows/self-routine.yml`:

```yaml
name: Self — Repository Routines

on:
  schedule:
    - cron: "0 3 * * 1"
  pull_request:
    types: [closed]
  push:
    branches: [main]
    paths:
      - .github/labels.yml
  workflow_dispatch:
    inputs:
      routine:
        description: Routine to run
        type: choice
        options:
          - all
          - branch-cleanup-stale
          - stale-pr
          - stale-issue
          - labels-sync
          - workflow-runs-cleanup
        default: all
      dry_run:
        description: Preview changes without applying them
        type: boolean
        default: true

permissions:
  contents: write
  pull-requests: write
  issues: write
  actions: write

jobs:
  routine:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/routine.yml@v1
    with:
      routine: ${{ inputs.routine || 'all' }}
      dry_run: ${{ inputs.dry_run || false }}
      merged_branch: ${{ github.head_ref }}
    secrets: inherit
```

### Customizing thresholds

```yaml
jobs:
  routine:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/routine.yml@v1
    with:
      routine: all
      branch_stale_days: 45
      pr_days_before_stale: 30
      pr_days_before_close: 14
      issue_days_before_stale: 60
      workflow_runs_retention_days: 90
      merged_branch: ${{ github.head_ref }}
    secrets: inherit
```

### Adding extra protected branches

Use `extra_protected_branches` when you only want to add patterns to the default and keep the rest:

```yaml
jobs:
  routine:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/routine.yml@v1
    with:
      extra_protected_branches: "develop-*,feature-stable"
      merged_branch: ${{ github.head_ref }}
    secrets: inherit
```

Use `protected_branches` to fully override the default (not recommended unless you really need to drop one of the standard patterns):

```yaml
jobs:
  routine:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/routine.yml@v1
    with:
      protected_branches: "main,trunk,prod-*"
      merged_branch: ${{ github.head_ref }}
    secrets: inherit
```

### Testing on a feature branch

```yaml
jobs:
  routine:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/routine.yml@develop
    with:
      routine: all
      dry_run: true
      merged_branch: ${{ github.head_ref }}
    secrets: inherit
```

## Notes

- The `pull_request` trigger must include `types: [closed]`. The merged-branch job filters for `github.event.pull_request.merged == true` internally.
- The `push` trigger is intended for `branches: [main]` with `paths: [.github/labels.yml]`. Pushes to other branches do not trigger label sync.
- Sub-workflows are referenced by major-version tag (`@v1`) so patch and minor updates flow automatically. To freeze, fork the entrypoint and pin to a specific `@vX.Y.Z`.
