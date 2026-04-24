<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>workflow-runs-cleanup</h1></td>
  </tr>
</table>

Composite action that deletes old GitHub Actions workflow runs to keep the repository within the Actions storage budget. Wraps [Mattraks/delete-workflow-runs](https://github.com/Mattraks/delete-workflow-runs).

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `github-token` | GitHub token with `actions:write` | Yes | — |
| `retention-days` | Delete runs older than this many days | No | `90` |
| `keep-minimum-runs` | Minimum runs to retain per workflow | No | `10` |
| `delete-workflow-pattern` | Workflow name or filename to target (empty = all) | No | `""` |
| `delete-run-by-conclusion-pattern` | Comma-separated conclusions to target, or `ALL` | No | `ALL` |
| `delete-workflow-by-state-pattern` | Comma-separated states to target, or `ALL` | No | `ALL` |
| `dry-run` | Preview deletions without applying them | No | `false` |

## Usage

### As a composite action

```yaml
jobs:
  cleanup:
    runs-on: ubuntu-latest
    permissions:
      actions: write
    steps:
      - uses: LerianStudio/github-actions-shared-workflows/src/config/workflow-runs-cleanup@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          retention-days: "90"
          dry-run: "true"
```

### As a reusable workflow (recommended)

```yaml
jobs:
  cleanup:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/workflow-runs-cleanup.yml@v1
    with:
      retention_days: 90
      dry_run: false
    secrets: inherit
```

## Permissions required

```yaml
permissions:
  actions: write
```
