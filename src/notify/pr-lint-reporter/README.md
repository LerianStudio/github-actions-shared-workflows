<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>pr-lint-reporter</h1></td>
  </tr>
</table>

Posts a formatted lint analysis summary as a PR comment, aggregating results from all lint jobs. Updates the comment on subsequent runs instead of creating new ones.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `github-token` | GitHub token with `pull-requests:write`, `issues:write` and `checks:read` permissions | Yes | — |
| `yamllint-result` | Result of the yamllint job | No | `skipped` |
| `yamllint-files` | Space-separated list of YAML files linted | No | `` |
| `actionlint-result` | Result of the actionlint job | No | `skipped` |
| `actionlint-files` | Comma-separated list of workflow files linted | No | `` |
| `pinned-actions-result` | Result of the pinned-actions job | No | `skipped` |
| `pinned-actions-files` | Comma-separated list of files checked | No | `` |
| `markdown-result` | Result of the markdown-link-check job | No | `skipped` |
| `markdown-files` | Comma-separated list of markdown files checked | No | `` |
| `typos-result` | Result of the typos job | No | `skipped` |
| `typos-files` | Space-separated list of files checked for typos | No | `` |
| `shellcheck-result` | Result of the shellcheck job | No | `skipped` |
| `shellcheck-files` | Comma-separated list of YAML files checked by shellcheck | No | `` |
| `readme-result` | Result of the readme-check job | No | `skipped` |
| `readme-files` | Comma-separated list of files checked for README presence | No | `` |

## Usage as composite step

```yaml
jobs:
  lint-report:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    needs: [yamllint, actionlint, pinned-actions, markdown-link-check, typos, shellcheck, readme-check]
    if: always() && github.event_name == 'pull_request'
    steps:
      - name: Checkout
        uses: actions/checkout@v6

      - name: Post Lint Report
        uses: LerianStudio/github-actions-shared-workflows/src/notify/pr-lint-reporter@develop
        with:
          github-token: ${{ secrets.MANAGE_TOKEN || github.token }}
          yamllint-result: ${{ needs.yamllint.result }}
          actionlint-result: ${{ needs.actionlint.result }}
          shellcheck-result: ${{ needs.shellcheck.result }}
          readme-result: ${{ needs.readme-check.result }}
```

## Required permissions

```yaml
permissions:
  pull-requests: write
  issues: write
  checks: read
```
