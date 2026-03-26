<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>pr-blocking-collect</h1></td>
  </tr>
</table>

Collects outcomes from blocking validation checks, writes them as job outputs, and fails the job if any check failed. Used as the final step in the blocking-checks tier of the pr-validation workflow.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `source-branch-outcome` | Outcome of the source branch validation step | No | `skipped` |
| `title-outcome` | Outcome of the PR title validation step | Yes | |
| `description-outcome` | Outcome of the PR description validation step | Yes | |

## Outputs

| Output | Description |
|--------|-------------|
| `source_branch` | Outcome of source branch validation |
| `title` | Outcome of PR title validation |
| `description` | Outcome of PR description validation |

## Usage as composite step

```yaml
- name: Collect results and enforce blocking
  id: collect
  uses: LerianStudio/github-actions-shared-workflows/src/validate/pr-blocking-collect@v1.x.x
  with:
    source-branch-outcome: ${{ steps.source-branch.outcome || 'skipped' }}
    title-outcome: ${{ steps.title.outcome }}
    description-outcome: ${{ steps.description.outcome }}
```

## Required permissions

```yaml
permissions:
  contents: read
```
