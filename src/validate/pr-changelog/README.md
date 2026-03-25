<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>pr-changelog</h1></td>
  </tr>
</table>

Checks if `CHANGELOG.md` was updated in the PR diff. Outputs the result for use by downstream jobs (e.g., summary reporting).

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `base-ref` | Base branch for diff comparison | Yes | |

## Outputs

| Output | Description |
|--------|-------------|
| `updated` | Whether CHANGELOG.md was updated (`true`/`false`) |

## Usage as composite step

```yaml
jobs:
  pr-changelog:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - name: Checkout
        uses: actions/checkout@v6
        with:
          fetch-depth: 0

      - name: Check Changelog
        uses: LerianStudio/github-actions-shared-workflows/src/validate/pr-changelog@v1.x.x
        with:
          base-ref: ${{ github.base_ref }}
```

## Required permissions

```yaml
permissions:
  contents: read
```
