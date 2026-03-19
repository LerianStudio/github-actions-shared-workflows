<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>composite-schema</h1></td>
  </tr>
</table>

Validate that composite action `inputs` follow project conventions:

- Every input has a non-empty `description`
- `required: true` inputs must **not** have a `default`
- `required: false` inputs **must** have a `default`

Only files under `src/` whose `runs.using` is `composite` are validated; all others are silently skipped.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `files` | Comma-separated list of YAML files to check (empty = skip) | No | `` |

## Usage as composite step

```yaml
jobs:
  composite-schema:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - name: Checkout
        uses: actions/checkout@v6

      - name: Composite Schema Lint
        uses: LerianStudio/github-actions-shared-workflows/src/lint/composite-schema@develop
        with:
          files: "src/lint/my-check/action.yml,src/build/my-build/action.yml"
```

## Required permissions

```yaml
permissions:
  contents: read
```
