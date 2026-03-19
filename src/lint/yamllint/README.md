<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>yamllint</h1></td>
  </tr>
</table>

Validate YAML files using [yamllint](https://github.com/adrienverge/yamllint).

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `config-file` | Path to the yamllint configuration file | No | `.yamllint.yml` |
| `file-or-dir` | Space-separated list of files or directories to lint | No | `.` |
| `strict` | Treat warnings as errors | No | `false` |

## Usage as composite step

```yaml
- name: Checkout
  uses: actions/checkout@v4

- name: YAML Lint
  uses: LerianStudio/github-actions-shared-workflows/src/lint/yamllint@v1.2.3
  with:
    file-or-dir: ".github/workflows/ src/"
    config-file: ".yamllint.yml"
```

## Usage via reusable workflow

```yaml
jobs:
  lint:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-lint.yml@v1.2.3
    secrets: inherit
```

## Required permissions

```yaml
permissions:
  contents: read
```
