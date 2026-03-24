<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>pr-size</h1></td>
  </tr>
</table>

Calculates PR size based on changed lines, adds a size label (`size/XS` through `size/XL`), and comments on extra-large PRs suggesting they be broken up.

| Lines Changed | Label |
|---------------|-------|
| < 50 | `size/XS` |
| 50–199 | `size/S` |
| 200–499 | `size/M` |
| 500–999 | `size/L` |
| >= 1000 | `size/XL` |

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `github-token` | GitHub token with pull-requests write permission | Yes | |
| `base-ref` | Base branch for diff comparison | Yes | |
| `dry-run` | When true, calculate size without adding labels or comments | No | `false` |

## Outputs

| Output | Description |
|--------|-------------|
| `size` | PR size category (XS, S, M, L, XL) |
| `changed-lines` | Number of changed lines |

## Usage as composite step

```yaml
jobs:
  pr-size:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - name: Checkout
        uses: actions/checkout@v6
        with:
          fetch-depth: 0

      - name: Check PR Size
        uses: LerianStudio/github-actions-shared-workflows/src/validate/pr-size@v1.x.x
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          base-ref: ${{ github.base_ref }}
```

## Required permissions

```yaml
permissions:
  contents: read
  pull-requests: write
```
