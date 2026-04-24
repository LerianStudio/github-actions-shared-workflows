<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>workflow-runs-cleanup</h1></td>
  </tr>
</table>

Reusable workflow that deletes old GitHub Actions workflow runs. Wraps the [`workflow-runs-cleanup`](../src/config/workflow-runs-cleanup/README.md) composite. Intended for monthly scheduled runs to keep Actions storage within limits.

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `retention_days` | Delete runs older than this many days | No | `90` |
| `keep_minimum_runs` | Minimum runs to retain per workflow | No | `10` |
| `delete_workflow_pattern` | Workflow name or filename to target (empty = all; literal substring match, wildcards do not expand) | No | `""` |
| `delete_run_by_conclusion_pattern` | Comma-separated conclusions to target, or `ALL` | No | `ALL` |
| `delete_workflow_by_state_pattern` | Comma-separated states to target, or `ALL` | No | `ALL` |
| `dry_run` | Preview deletions without applying them | No | `false` |

## Usage

### Testing (against `@develop`)

```yaml
jobs:
  cleanup:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/workflow-runs-cleanup.yml@develop
    with:
      dry_run: true
    secrets: inherit
```

### Production (pinned)

```yaml
jobs:
  cleanup:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/workflow-runs-cleanup.yml@v1.19.0
    with:
      retention_days: 90
    secrets: inherit
```

## Permissions required

```yaml
permissions:
  actions: write
```
