<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>markdown-link-check</h1></td>
  </tr>
</table>

Validate that links in markdown files are not broken using [markdown-link-check](https://github.com/tcort/markdown-link-check).

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `file-path` | Comma-separated list of markdown files to check | No | `` |
| `config-file` | Path to the markdown-link-check configuration file | No | `.github/markdown-link-check-config.json` |

## Usage as composite step

```yaml
- name: Checkout
  uses: actions/checkout@v4

- name: Markdown Link Check
  uses: LerianStudio/github-actions-shared-workflows/src/lint/markdown-link-check@v1.2.3
  with:
    file-path: "README.md,docs/go-ci.md"
    config-file: ".github/markdown-link-check-config.json"
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
