<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>codeql-init</h1></td>
  </tr>
</table>

Composite action that wraps [`github/codeql-action/init`](https://github.com/github/codeql-action) to initialize CodeQL analysis for specified languages. Uses the `security-extended` query suite by default for broader coverage. Designed to be paired with [`codeql-analyze`](../codeql-analyze/).

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `languages` | Languages to analyze (comma-separated, e.g., `actions`, `javascript-typescript`, `go`) | Yes | — |
| `queries` | Query suite to use (`security-standard`, `security-extended`, `security-and-quality`) | No | `security-extended` |
| `config-file` | Path to CodeQL configuration file | No | — |

## Usage

### Basic (GitHub Actions YAML analysis)

```yaml
jobs:
  codeql:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    permissions:
      contents: read
      security-events: write
      actions: read
    steps:
      - uses: actions/checkout@v6

      - name: Initialize CodeQL
        uses: LerianStudio/github-actions-shared-workflows/src/security/codeql-init@v1.x.x
        with:
          languages: actions

      - name: Analyze
        uses: LerianStudio/github-actions-shared-workflows/src/security/codeql-analyze@v1.x.x
        with:
          category: '/language:actions'
```

### Multiple languages

```yaml
- name: Initialize CodeQL
  uses: LerianStudio/github-actions-shared-workflows/src/security/codeql-init@v1.x.x
  with:
    languages: javascript-typescript
    queries: security-and-quality
```

## Permissions required

```yaml
permissions:
  contents: read
  security-events: write
  actions: read  # required for workflows using private repositories
```
