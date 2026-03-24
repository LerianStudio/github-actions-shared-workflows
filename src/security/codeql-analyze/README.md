<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>codeql-analyze</h1></td>
  </tr>
</table>

Composite action that performs CodeQL analysis and uploads SARIF results to the GitHub Security tab. Designed to be paired with [`codeql-init`](../codeql-init/).

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `category` | Category for SARIF results used for deduplication (e.g., `/language:actions`) | Yes | — |
| `output` | Output directory for SARIF files | No | `../results` |

## Usage

### Basic (paired with codeql-init)

```yaml
steps:
  - uses: actions/checkout@v6

  - name: Initialize CodeQL
    uses: LerianStudio/github-actions-shared-workflows/src/security/codeql-init@v1.x.x
    with:
      languages: actions

  - name: Perform CodeQL Analysis
    uses: LerianStudio/github-actions-shared-workflows/src/security/codeql-analyze@v1.x.x
    with:
      category: '/language:actions'
```

## Permissions required

```yaml
permissions:
  contents: read
  security-events: write  # required for SARIF upload to GitHub Security tab
  actions: read            # required for workflows using private repositories
```
