<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>changed-paths</h1></td>
  </tr>
</table>

Composite action that detects changed files between commits and outputs a matrix of changed directories. Designed for monorepo setups to trigger builds only for components that have changed.

## Inputs

> **Breaking change (kebab-case):** All input names were renamed from `snake_case` to `kebab-case`. Update any callers that used the old names:
>
> | Old (snake_case) | New (kebab-case) |
> |---|---|
> | `filter_paths` | `filter-paths` |
> | `shared_paths` | `shared-paths` |
> | `path_level` | `path-level` |
> | `get_app_name` | `get-app-name` |
> | `app_name_prefix` | `app-name-prefix` |
> | `app_name_overrides` | `app-name-overrides` |
> | `normalize_to_filter` | `normalize-to-filter` |
> | `ignore_dirs` | `ignore-dirs` |
> | `fallback_app_name` | `fallback-app-name` |
> | `consolidate_to_root` | `consolidate-to-root` |
> | `consolidate_keep_dirs` | `consolidate-keep-dirs` |

| Input | Description | Required | Default |
|---|---|:---:|---|
| `filter-paths` | Newline-separated list of path prefixes to filter results. Also accepts JSON array format. | No | `''` |
| `shared-paths` | Newline-separated (or JSON array) path patterns that, when matched by any changed file, include ALL `filter-paths` components in the matrix (e.g., `go.mod`, `go.sum`, `libs/`) | No | `''` |
| `path-level` | Limits the path to the first N segments | No | `0` (disabled) |
| `get-app-name` | Output matrix with `name` and `working_dir` fields | No | `false` |
| `app-name-prefix` | Prefix to add to each app name | No | `''` |
| `app-name-overrides` | Newline-separated `path:name` mappings. Use `path:` for prefix-only | No | `''` |
| `normalize-to-filter` | Use filter path as `working_dir` instead of actual trimmed path | No | `false` |
| `ignore-dirs` | Newline-separated directories to exclude from the output matrix | No | `''` |
| `fallback-app-name` | When `filter-paths` is empty, return single-item matrix with this name | No | `''` |
| `consolidate-to-root` | Consolidate all entries (except `consolidate-keep-dirs`) to root | No | `false` |
| `consolidate-keep-dirs` | Newline-separated dirs to keep as-is during consolidation | No | `''` |

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
      filter-paths: '["components/api", "components/web"]'
      path-level: 2
      get-app-name: true
      app-name-prefix: 'myapp'
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
  app-name-overrides: |-
    components/onboarding:
    components/transaction:tx
  app-name-prefix: 'midaz'
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
  filter-paths: |-
    components/api
    components/web
  ignore-dirs: |-
    .github
    .githooks
  get-app-name: true
```

Directories matching `.github` or `.githooks` (exact or prefix) are excluded from the output matrix before app name generation.

### Single app mode (fallback_app_name)

When `filter_paths` is empty and `fallback_app_name` is set, the composite skips change detection and returns a single-item matrix:

```yaml
with:
  get-app-name: true
  fallback-app-name: 'my-service'
```

```json
[{"name": "my-service", "working_dir": "."}]
```

### Type 2 monorepo (consolidate_to_root)

When `consolidate_to_root: true`, all entries except those matching `consolidate_keep_dirs` are consolidated into a single root entry using `fallback_app_name`:

```yaml
with:
  filter-paths: |-
    components/api
    components/worker
    frontend
  get-app-name: true
  fallback-app-name: 'my-repo'
  consolidate-to-root: true
  consolidate-keep-dirs: 'frontend'
  ignore-dirs: |-
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

### With shared-paths (monorepo root-level files)

When root-level files like `go.mod` or `go.sum` change, all components should be rebuilt. Use `shared-paths` to trigger a full matrix whenever such files are touched:

```yaml
with:
  filter-paths: |-
    components/manager
    components/worker
  shared-paths: |-
    go.mod
    go.sum
    libs/
  path-level: 2
  get-app-name: true
```

If only `go.mod` changes → both `components/manager` and `components/worker` are included in the matrix.
If only `components/worker/cmd/main.go` changes → only `components/worker` is included (normal behaviour).

### With normalize-to-filter

When `normalize-to-filter: true`, deeper changed paths are normalized back to the matching filter path.

Changed file `components/app/cmd/main.go` with `filter-paths: '["components/app"]'` outputs `working_dir: "components/app"` instead of `components/app/cmd`.

## How path-level works

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
