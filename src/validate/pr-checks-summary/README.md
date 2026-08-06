<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>pr-checks-summary</h1></td>
  </tr>
</table>

Generates a summary table of all PR validation check results in the GitHub Actions job summary, grouped by tier (Blocking / Advisory).

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `source-branch-result` | Result of source branch validation | No | `skipped` |
| `title-result` | Result of PR title validation | No | `skipped` |
| `description-result` | Result of PR description check | No | `skipped` |
| `size-result` | Result of PR size check | No | `skipped` |
| `label-result` | Result of auto-label step | No | `skipped` |
| `metadata-result` | Result of PR metadata check | No | `skipped` |
| `breaking-change-result` | Result of the breaking change guard | No | `skipped` |
| `dry-run` | Whether this is a dry run | No | `false` |

When `breaking-change-result` is `skipped` or omitted, the summary omits the guard row and preserves existing behavior. This optional default exists only for backward compatibility with direct action consumers. The mandatory `pr-validation` integration always supplies the guard result and offers no guard opt-out.

## Usage as composite step

```yaml
jobs:
  pr-checks-summary:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    needs: [blocking-checks, advisory-checks]
    if: always()
    steps:
      - name: PR Checks Summary
        uses: LerianStudio/github-actions-shared-workflows/src/validate/pr-checks-summary@v1.x.x
        with:
          source-branch-result: ${{ needs.blocking-checks.outputs.source-branch-result || 'skipped' }}
          title-result: ${{ needs.blocking-checks.outputs.title-result || 'skipped' }}
          description-result: ${{ needs.blocking-checks.outputs.description-result || 'skipped' }}
          size-result: ${{ needs.advisory-checks.outputs.size-result || 'skipped' }}
          label-result: ${{ needs.advisory-checks.outputs.label-result || 'skipped' }}
          metadata-result: ${{ needs.advisory-checks.outputs.metadata-result || 'skipped' }}
          breaking-change-result: ${{ needs.blocking-checks.outputs.breaking-change-result || 'skipped' }}
          dry-run: "true"
```

## Required permissions

```yaml
permissions:
  contents: read
```
