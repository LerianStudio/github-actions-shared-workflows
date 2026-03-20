<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>shellcheck</h1></td>
  </tr>
</table>

Run [shellcheck](https://github.com/koalaman/shellcheck) on all `run:` blocks embedded in GitHub Actions composite and workflow YAML files.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `files` | Comma-separated list of YAML files to check | No | `` |
| `severity` | Minimum severity to report and fail on (`error`, `warning`, `info`, `style`) | No | `warning` |

## Usage as composite step

```yaml
jobs:
  shellcheck:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - name: Checkout
        uses: actions/checkout@v6

      - name: Shell Check
        uses: LerianStudio/github-actions-shared-workflows/src/lint/shellcheck@develop
        with:
          files: ".github/workflows/ci.yml,src/lint/my-check/action.yml"
```

## Required permissions

```yaml
permissions:
  contents: read
```
