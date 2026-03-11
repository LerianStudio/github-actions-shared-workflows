<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>changed-paths</h1></td>
  </tr>
</table>

Reusable workflow for detecting changed paths between commits. Wraps the [`src/config/changed-paths`](../src/config/changed-paths/) composite action, adding `dry_run` support and `workflow_dispatch` for manual testing.

## Usage

### Basic Usage

```yaml
jobs:
  detect-changes:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/changed-paths.yml@v1.0.0

  build:
    needs: detect-changes
    if: needs.detect-changes.outputs.has_changes == 'true'
    runs-on: blacksmith-4vcpu-ubuntu-2404
    strategy:
      matrix:
        path: ${{ fromJson(needs.detect-changes.outputs.matrix) }}
    steps:
      - name: Build changed component
        run: echo "Building ${{ matrix.path }}"
```

### Monorepo with Path Filtering

```yaml
jobs:
  detect-changes:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/changed-paths.yml@v1.0.0
    with:
      filter_paths: '["components/api", "components/web", "components/worker"]'
      path_level: 2
```

### With App Name Generation

```yaml
jobs:
  detect-changes:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/changed-paths.yml@v1.0.0
    with:
      filter_paths: '["components/onboarding", "components/transaction", "components/ledger"]'
      path_level: 2
      get_app_name: true
      app_name_prefix: 'midaz'

  deploy:
    needs: detect-changes
    if: needs.detect-changes.outputs.has_changes == 'true'
    runs-on: blacksmith-4vcpu-ubuntu-2404
    strategy:
      matrix:
        app: ${{ fromJson(needs.detect-changes.outputs.matrix) }}
    steps:
      - uses: actions/checkout@v6
      - name: Deploy
        run: |
          echo "Deploying app: ${{ matrix.app.name }}"
          echo "Working directory: ${{ matrix.app.working_dir }}"
```

### With App Name Overrides

```yaml
jobs:
  detect-changes:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/changed-paths.yml@v1.0.0
    with:
      filter_paths: '["components/onboarding", "components/transaction"]'
      path_level: 2
      get_app_name: true
      app_name_prefix: 'midaz'
      app_name_overrides: |-
        components/onboarding:
        components/transaction:tx
```

### Dry Run

```yaml
jobs:
  test:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/changed-paths.yml@develop
    with:
      filter_paths: '["src/"]'
      path_level: 2
      dry_run: true
```

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `filter_paths` | JSON array of path prefixes to filter results | No | `''` |
| `path_level` | Limits the path to the first N segments | No | `0` (disabled) |
| `get_app_name` | Output matrix with `name` and `working_dir` fields | No | `false` |
| `app_name_prefix` | Prefix to add to each app name | No | `''` |
| `app_name_overrides` | Newline-separated `path:name` mappings. Use `path:` for prefix-only | No | `''` |
| `normalize_to_filter` | Use filter path as `working_dir` instead of actual trimmed path | No | `false` |
| `runner_type` | GitHub runner type | No | `blacksmith-4vcpu-ubuntu-2404` |
| `dry_run` | Preview changes without applying them | No | `false` |

## Outputs

| Output | Description |
|---|---|
| `matrix` | JSON array of changed directories (or objects if `get_app_name` is true) |
| `has_changes` | Boolean string (`'true'` or `'false'`) indicating if changes were detected |

## Related

- [Composite action documentation](../src/config/changed-paths/README.md)
