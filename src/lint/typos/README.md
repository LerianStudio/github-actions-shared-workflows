<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>typos</h1></td>
  </tr>
</table>

Detect typos in source code and documentation using [typos-cli](https://github.com/crate-ci/typos).

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `config` | Path to a typos configuration file (`_typos.toml`) | No | `` |

## Usage as composite step

```yaml
- name: Checkout
  uses: actions/checkout@v4

- name: Spelling Check
  uses: LerianStudio/github-actions-shared-workflows/src/lint/typos@v1.2.3
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
