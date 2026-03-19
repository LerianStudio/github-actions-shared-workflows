<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>changed-paths</h1></td>
  </tr>
</table>

Composite action that detects changed files between commits and outputs a matrix of changed directories. Designed for monorepo setups to trigger builds only for components that have changed.

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `filter_paths` | JSON array of path prefixes to filter results | No | `''` |
| `shared_paths` | Newline-separated (or JSON array) path patterns that, when matched by any changed file, include ALL `filter_paths` components in the matrix (e.g., `go.mod`, `go.sum`, `libs/`) | No | `''` |
| `path_level` | Limits the path to the first N segments | No | `0` (disabled) |
| `get_app_name` | Output matrix with `name` and `working_dir` fields | No | `false` |
| `app_name_prefix` | Prefix to add to each app name | No | `''` |
| `app_name_overrides` | Newline-separated `path:name` mappings. Use `path:` for prefix-only | No | `''` |
| `normalize_to_filter` | Use filter path as `working_dir` instead of actual trimmed path | No | `false` |
| `ignore_dirs` | Newline-separated directories to exclude from the output matrix | No | `''` |
| `fallback_app_name` | When `filter_paths` is empty, return single-item matrix with this name | No | `''` |
| `consolidate_to_root` | Consolidate all entries (except `consolidate_keep_dirs`) to root | No | `false` |
| `consolidate_keep_dirs` | Newline-separated dirs to keep as-is during consolidation | No | `''` |

## Outputs

| Output | Description |
|---|---|
| `matrix` | JSON array of changed directories (or objects with `name` and `working_dir`) |
| `has_changes` | `'true'` or `'false'` indicating if changes were detected |

## Usage as composite step

```yaml
steps:
  - name: Get changed paths
    id: changed-paths
    uses: LerianStudio/github-actions-shared-workflows/src/config/changed-paths@v1.0.0
    with:
      filter_paths: '["components/api", "components/web"]'
      path_level: 2
      get_app_name: true
      app_name_prefix: 'myapp'
```

## Output formats

### Default (get_app_name: false)

```json
["components/api", "components/web"]
```

### With app names (get_app_name: true)

```json
[
  {"name": "api", "working_dir": "components/api"},
  {"name": "web", "working_dir": "components/web"}
]
```

### With prefix (app_name_prefix: "myapp")

```json
[
  {"name": "myapp-api", "working_dir": "components/api"},
  {"name": "myapp-web", "working_dir": "components/web"}
]
```

### With overrides

```yaml
with:
  app_name_overrides: |-
    components/onboarding:
    components/transaction:tx
  app_name_prefix: 'midaz'
```

```json
[
  {"name": "midaz", "working_dir": "components/onboarding"},
  {"name": "midaz-tx", "working_dir": "components/transaction"}
]
```

### With ignore_dirs

```yaml
with:
  filter_paths: |-
    components/api
    components/web
  ignore_dirs: |-
    .github
    .githooks
  get_app_name: true
```

Directories matching `.github` or `.githooks` (exact or prefix) are excluded from the output matrix before app name generation.

### Single app mode (fallback_app_name)

When `filter_paths` is empty and `fallback_app_name` is set, the composite skips change detection and returns a single-item matrix:

```yaml
with:
  get_app_name: true
  fallback_app_name: 'my-service'
```

```json
[{"name": "my-service", "working_dir": "."}]
```

### Type 2 monorepo (consolidate_to_root)

When `consolidate_to_root: true`, all entries except those matching `consolidate_keep_dirs` are consolidated into a single root entry using `fallback_app_name`:

```yaml
with:
  filter_paths: |-
    components/api
    components/worker
    frontend
  get_app_name: true
  fallback_app_name: 'my-repo'
  consolidate_to_root: true
  consolidate_keep_dirs: 'frontend'
  ignore_dirs: |-
    .github
    .githooks
```

If `components/api` and `frontend` both changed:

```json
[
  {"name": "my-repo", "working_dir": "."},
  {"name": "frontend", "working_dir": "frontend"}
]
```

### With shared_paths (monorepo root-level files)

When root-level files like `go.mod` or `go.sum` change, all components should be rebuilt. Use `shared_paths` to trigger a full matrix whenever such files are touched:

```yaml
with:
  filter_paths: |-
    components/manager
    components/worker
  shared_paths: |-
    go.mod
    go.sum
    libs/
  path_level: 2
  get_app_name: true
```

If only `go.mod` changes → both `components/manager` and `components/worker` are included in the matrix.
If only `components/worker/cmd/main.go` changes → only `components/worker` is included (normal behaviour).

### With normalize_to_filter

When `normalize_to_filter: true`, deeper changed paths are normalized back to the matching filter path.

Changed file `components/app/cmd/main.go` with `filter_paths: '["components/app"]'` outputs `working_dir: "components/app"` instead of `components/app/cmd`.

## How path_level works

| Original Path | path_level | Result |
|---|---|---|
| `components/api/src/main.go` | 1 | `components` |
| `components/api/src/main.go` | 2 | `components/api` |
| `components/api/src/main.go` | 3 | `components/api/src` |
| `services/auth/handlers/login.ts` | 2 | `services/auth` |

## Event support

| Event | Diff strategy |
|---|---|
| `pull_request` / `pull_request_target` | Base SHA vs HEAD |
| `push` | `before` SHA vs `sha` |
| Tag / first commit | `HEAD^` vs HEAD (fallback: `ls-tree`) |

## Required permissions

```yaml
permissions:
  contents: read
```

## Requirements

This action uses `jq` for JSON processing, which is preinstalled on all GitHub-hosted runners.
