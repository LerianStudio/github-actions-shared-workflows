<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>pr-labels</h1></td>
  </tr>
</table>

Automatically adds labels to a PR based on changed files using the [actions/labeler](https://github.com/actions/labeler) configuration.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `github-token` | GitHub token with pull-requests write permission | Yes | |
| `config-path` | Path to labeler configuration file | No | `.github/labeler.yml` |

## Usage as composite step

```yaml
jobs:
  pr-labels:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - name: Checkout
        uses: actions/checkout@v6
        with:
          fetch-depth: 0

      - name: Auto-label PR
        uses: LerianStudio/github-actions-shared-workflows/src/validate/pr-labels@v1.x.x
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

## Required permissions

```yaml
permissions:
  contents: read
  pull-requests: write
```
