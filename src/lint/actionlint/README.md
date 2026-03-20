<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>actionlint</h1></td>
  </tr>
</table>

Validate GitHub Actions workflow syntax using [actionlint](https://github.com/rhysd/actionlint).

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `files` | Comma-separated glob patterns of workflow files to lint | No | `.github/workflows/*.yml` |
| `shellcheck` | Enable shellcheck integration for `run:` blocks | No | `true` |
| `fail-on-error` | Fail the step on lint errors | No | `true` |

## Usage as composite step

```yaml
- name: Checkout
  uses: actions/checkout@v4

- name: Action Lint
  uses: LerianStudio/github-actions-shared-workflows/src/lint/actionlint@v1.2.3
  with:
    files: ".github/workflows/*.yml"
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
