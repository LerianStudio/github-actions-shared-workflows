<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>resolve-target</h1></td>
  </tr>
</table>

Composite action that resolves the deployed environment for an E2E run from the
release tag and tenancy, and selects which candidate modules to actually run by
intersecting them with the components that were built. Requires the end-to-end
suite repository to be checked out first (it validates each module against a
`cases/<module>` directory).

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `ref-name` | Git ref name (`github.ref_name`); `-beta.*`→dev, `-rc.*`→stg, else→prd | Yes | — |
| `tenancy` | Tenancy mode — `st` or `mt` | No | `st` |
| `modules` | Comma-separated candidate modules (each a valid `cases/<module>`) | Yes | — |
| `built-apps` | JSON array of built components (`[{"name":...}]`); candidates are intersected with it when non-empty | No | `[]` |

## Outputs

| Output | Description |
|--------|-------------|
| `base_env` | Resolved base environment — `dev`/`stg`/`prd` |
| `env_name` | Env-file suffix — `benedita-<base_env>-<tenancy>` |
| `modules` | Comma-separated selected modules (after intersection) |
| `has_modules` | `"true"`/`"false"` — whether any module was selected (`false` = no-op) |

## Usage as composite step

```yaml
jobs:
  e2e:
    needs: build                       # build.outputs.matrix drives module selection
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - uses: actions/checkout@v4
        with:
          repository: LerianStudio/end-to-end
          token: ${{ secrets.e2e_repo_token }}
      - name: Resolve E2E target
        id: plan
        uses: LerianStudio/github-actions-shared-workflows/src/e2e/resolve-target@v1
        with:
          ref-name: ${{ github.ref_name }}
          tenancy: st
          modules: "midaz-ledger,midaz-crm"
          built-apps: ${{ needs.build.outputs.matrix }}
```

## Usage via reusable workflow

Used internally by `end-to-end-tests.yml`; callers configure it through that
workflow's `modules` / `built_apps` / `tenancy` inputs.

## Required permissions

```yaml
permissions:
  contents: read
```
