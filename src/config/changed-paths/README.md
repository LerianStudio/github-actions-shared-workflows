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
| `path_level` | Limits the path to the first N segments | No | `0` (disabled) |
| `get_app_name` | Output matrix with `name` and `working_dir` fields | No | `false` |
| `app_name_prefix` | Prefix to add to each app name | No | `''` |
| `app_name_overrides` | Newline-separated `path:name` mappings. Use `path:` for prefix-only | No | `''` |
| `normalize_to_filter` | Use filter path as `working_dir` instead of actual trimmed path | No | `false` |

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
