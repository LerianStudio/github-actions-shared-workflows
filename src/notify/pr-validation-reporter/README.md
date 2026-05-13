<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>pr-validation-reporter</h1></td>
  </tr>
</table>

Posts a single mergeability summary comment aggregating all PR validation check results (blocking + advisory). Updates the same comment on subsequent runs via a stable HTML marker instead of stacking new ones.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `github-token` | GitHub token with `pull-requests:write` and `issues:write` permissions | Yes | — |
| `source-branch-result` | Result of source branch validation | No | `skipped` |
| `title-result` | Result of PR title validation | No | `skipped` |
| `description-result` | Result of PR description validation | No | `skipped` |
| `size-result` | Result of PR size check | No | `skipped` |
| `label-result` | Result of auto-label step | No | `skipped` |
| `metadata-result` | Result of PR metadata check | No | `skipped` |
| `dry-run` | When `true`, skip posting the summary comment | No | `false` |

## Usage as composite step

```yaml
jobs:
  pr-validation-report:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    needs: [blocking-checks, advisory-checks]
    if: always() && github.event.pull_request.draft != true
    steps:
      - name: Post PR Validation Summary
        uses: LerianStudio/github-actions-shared-workflows/src/notify/pr-validation-reporter@v1.x.x
        with:
          github-token: ${{ secrets.MANAGE_TOKEN || github.token }}
          source-branch-result: ${{ needs.blocking-checks.outputs.source-branch-result }}
          title-result: ${{ needs.blocking-checks.outputs.title-result }}
          description-result: ${{ needs.blocking-checks.outputs.description-result }}
          size-result: ${{ needs.advisory-checks.outputs.size-result }}
          label-result: ${{ needs.advisory-checks.outputs.label-result }}
          metadata-result: ${{ needs.advisory-checks.outputs.metadata-result }}
```

## Required permissions

```yaml
permissions:
  pull-requests: write
  issues: write
```

## Comment marker

The composite upserts a comment identified by:

```html
<!-- pr-validation-report -->
```
