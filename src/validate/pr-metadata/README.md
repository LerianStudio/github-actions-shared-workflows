<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>pr-metadata</h1></td>
  </tr>
</table>

Auto-assigns the PR author as assignee when no one is assigned. Skips bot accounts (dependabot, github-actions, etc).

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `github-token` | GitHub token with pull-requests write permission | Yes | |

## Usage as composite step

```yaml
jobs:
  pr-metadata:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - name: Auto-assign PR author
        uses: LerianStudio/github-actions-shared-workflows/src/validate/pr-metadata@v1.x.x
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

## Required permissions

```yaml
permissions:
  pull-requests: write
```
