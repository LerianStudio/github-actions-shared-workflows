<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>pr-metadata</h1></td>
  </tr>
</table>

Checks PR metadata quality: warns if no assignees are set and if no issues are linked via keywords (`Closes`, `Fixes`, `Resolves`, `Relates to`).

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `github-token` | GitHub token for API access | Yes | |

## Usage as composite step

```yaml
jobs:
  pr-metadata:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - name: Check PR Metadata
        uses: LerianStudio/github-actions-shared-workflows/src/validate/pr-metadata@v1.x.x
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

## Required permissions

```yaml
permissions:
  pull-requests: read
```
