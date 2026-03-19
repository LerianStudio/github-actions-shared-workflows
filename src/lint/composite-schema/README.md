<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>composite-schema</h1></td>
  </tr>
</table>

Validate that composite actions under `src/` follow project conventions. Checks performed:

**Root level**
- `name` field is present and non-empty
- `description` field is present and non-empty

**Steps**
- `runs.steps` is defined and non-empty
- Step count does not exceed 15 (split into smaller composites if so)

**Inputs**
- Every input has a non-empty `description`
- `required: true` inputs must **not** have a `default`
- `required: false` inputs **must** have a `default`
- Input names must be **kebab-case** (e.g. `github-token`, not `githubToken` or `github_token`)
- Input names must not use reserved prefixes: `GITHUB_*`, `ACTIONS_*`, `RUNNER_*`

Only files whose `runs.using` is `composite` are validated; all others are silently skipped.

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
