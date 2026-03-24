<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>pr-description</h1></td>
  </tr>
</table>

Validates PR description quality by checking minimum length and recommended sections (`Description`, `Type of Change`).

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `github-token` | GitHub token for API access | Yes | |
| `min-length` | Minimum PR description length in characters | No | `50` |

## Usage as composite step

```yaml
jobs:
  pr-description:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - name: Validate PR Description
        uses: LerianStudio/github-actions-shared-workflows/src/validate/pr-description@v1.x.x
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          min-length: "100"
```

## Required permissions

```yaml
permissions:
  pull-requests: read
```
