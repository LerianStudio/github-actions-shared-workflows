<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>codeql-reporter</h1></td>
  </tr>
</table>

Composite action that reads CodeQL SARIF output and posts a formatted security report as a PR comment. Uses an idempotent comment strategy (updates existing comment on re-runs). Designed to run after [`codeql-analyze`](../codeql-analyze/).

Findings parsed from SARIF are cross-referenced with the Code Scanning REST API (`listAlertsForRepo` on `refs/pull/<pr>/merge`) so alerts that were **dismissed** via the Security tab or are already **fixed** on the merge ref do not show up in the PR comment. A footer notes the number of hidden findings so reviewers know the comment omitted some. If the API call fails (e.g. missing permissions), the action degrades gracefully to the SARIF-only view and emits a warning.

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `github-token` | GitHub token with `pull-requests:write` and `issues:write` permissions | Yes | — |
| `sarif-path` | Path to the CodeQL SARIF output directory | No | `../results` |
| `languages` | Comma-separated list of languages analyzed (for display) | Yes | — |
| `fail-on-findings` | Fail the step when security findings are detected (`true`/`false`) | No | `false` |

## Outputs

| Output | Description |
|---|---|
| `has-findings` | `true` if any CodeQL findings were detected |
| `findings-count` | Total number of CodeQL findings |

## Usage

### After CodeQL analysis (paired with codeql-init and codeql-analyze)

```yaml
steps:
  - uses: actions/checkout@v6

  - name: Initialize CodeQL
    uses: LerianStudio/github-actions-shared-workflows/src/security/codeql-init@v1.x.x
    with:
      languages: go

  - name: Perform CodeQL Analysis
    uses: LerianStudio/github-actions-shared-workflows/src/security/codeql-analyze@v1.x.x
    with:
      category: '/language:go'

  - name: Post CodeQL Results to PR
    if: always() && github.event_name == 'pull_request'
    uses: LerianStudio/github-actions-shared-workflows/src/security/codeql-reporter@v1.x.x
    with:
      github-token: ${{ github.token }}
      languages: go
```

## Permissions required

```yaml
permissions:
  contents: read
  security-events: write   # required for alert-state enrichment; `read` is enough on its own
  pull-requests: write
  actions: read
```

> `security-events: write` (already required by [`codeql-analyze`](../codeql-analyze/)) covers the `listAlertsForRepo` call used to filter dismissed/fixed alerts. If only `read` is granted the enrichment still works; if the permission is missing entirely the action falls back to the raw SARIF view with a warning.
