<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>readme-check</h1></td>
  </tr>
</table>

Ensure every composite action under `src/` has a sibling `README.md` file.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `files` | Comma-separated list of changed files to check | No | `` |

## Usage as composite step

```yaml
jobs:
  readme-check:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - name: Checkout
        uses: actions/checkout@v6

      - name: README Check
        uses: LerianStudio/github-actions-shared-workflows/src/lint/readme-check@v1.x.x
        with:
          files: "src/lint/my-check/action.yml,src/build/my-build/action.yml"
```

## Required permissions

```yaml
permissions:
  contents: read
```
