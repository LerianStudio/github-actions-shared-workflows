<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>pr-checks-summary</h1></td>
  </tr>
</table>

Generates a summary table of all PR validation check results in the GitHub Actions job summary.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `source-branch-result` | Result of source branch validation | No | `skipped` |
| `title-result` | Result of PR title validation | No | `skipped` |
| `size-result` | Result of PR size check | No | `skipped` |
| `description-result` | Result of PR description check | No | `skipped` |
| `label-result` | Result of auto-label step | No | `skipped` |
| `metadata-result` | Result of PR metadata check | No | `skipped` |
| `changelog-result` | Result of changelog check | No | `skipped` |
| `dry-run` | Whether this is a dry run | No | `false` |

## Usage as composite step

```yaml
jobs:
  pr-checks-summary:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    needs: [pr-source-branch, pr-title, pr-size, pr-description, pr-labels, pr-metadata, pr-changelog]
    if: always()
    steps:
      - name: PR Checks Summary
        uses: LerianStudio/github-actions-shared-workflows/src/validate/pr-checks-summary@v1.x.x
        with:
          source-branch-result: ${{ needs.pr-source-branch.result }}
          title-result: ${{ needs.pr-title.result }}
          size-result: ${{ needs.pr-size.result }}
          description-result: ${{ needs.pr-description.result }}
          label-result: ${{ needs.pr-labels.result }}
          metadata-result: ${{ needs.pr-metadata.result }}
          changelog-result: ${{ needs.pr-changelog.result }}
          dry-run: "true"
```

## Required permissions

```yaml
permissions:
  contents: read
```
