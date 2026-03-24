<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>codeql-config</h1></td>
  </tr>
</table>

Composite action that generates a dynamic CodeQL configuration file scoped to changed paths. Ensures CodeQL analyzes only modified files in PRs instead of the entire repository. Designed to run before [`codeql-init`](../codeql-init/).

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `changed-paths` | Comma or newline-separated list of changed file paths | Yes | — |
| `output-file` | Path where the generated config file will be written | No | `.github/codeql-config-pr.yml` |

## Outputs

| Output | Description |
|---|---|
| `config-file` | Path to the generated CodeQL config file |
| `skip` | `true` if no paths were resolved and CodeQL should be skipped |

## Usage

### With changed-workflows (this repo)

```yaml
- name: Generate CodeQL config
  id: codeql-config
  uses: LerianStudio/github-actions-shared-workflows/src/security/codeql-config@v1.x.x
  with:
    changed-paths: ${{ needs.changed-files.outputs.action_files }}

- name: Initialize CodeQL
  if: steps.codeql-config.outputs.skip != 'true'
  uses: LerianStudio/github-actions-shared-workflows/src/security/codeql-init@v1.x.x
  with:
    languages: actions
    config-file: ${{ steps.codeql-config.outputs.config-file }}
```

## Permissions required

No special permissions needed — this composite only generates a file.
