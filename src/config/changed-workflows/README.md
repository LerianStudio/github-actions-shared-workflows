<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>changed-workflows</h1></td>
  </tr>
</table>

Detect changed files in a pull request and categorize them by type for downstream lint jobs.

## Outputs

| Output | Format | Description |
|--------|--------|-------------|
| `yaml-files` | Space-separated | All changed `.yml` files |
| `workflow-files` | Comma-separated | Changed `.github/workflows/*.yml` files |
| `action-files` | Space-separated | Changed workflow and composite `.yml`/`.yaml` files |
| `markdown-files` | Comma-separated | Changed `.md` files |

On `workflow_dispatch`, falls back to scanning the full repository.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `github-token` | GitHub token for `gh` CLI access | No | `""` |

## Usage as composite step

```yaml
- name: Checkout
  uses: actions/checkout@v4

- name: Detect changed files
  id: changed
  uses: LerianStudio/github-actions-shared-workflows/src/config/changed-workflows@v1.2.3
  with:
    github-token: ${{ github.token }}

- name: YAML Lint
  if: steps.changed.outputs.yaml-files != ''
  uses: LerianStudio/github-actions-shared-workflows/src/lint/yamllint@v1.2.3
  with:
    file-or-dir: ${{ steps.changed.outputs.yaml-files }}
```

## Required permissions

```yaml
permissions:
  contents: read
  pull-requests: read
```
