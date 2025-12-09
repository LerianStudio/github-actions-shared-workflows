# Changed Paths Workflow

Reusable workflow for detecting changed paths between commits. Useful for monorepo setups to trigger builds only for components that have changed, enabling efficient CI/CD pipelines with matrix strategies.

## Features

- Detect changed files between commits
- Filter paths by prefix patterns
- Limit path depth to specific segments
- Generate app name matrix for monorepo deployments
- Customizable app name prefix
- Output suitable for GitHub Actions matrix strategy
- Handles edge cases (first commit, tags, missing refs)

## Usage

### Basic Usage

```yaml
name: CI
on:
  push:
    branches: [main]

jobs:
  detect-changes:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/changed-paths.yml@main

  build:
    needs: detect-changes
    if: needs.detect-changes.outputs.has_changes == 'true'
    runs-on: ubuntu-latest
    strategy:
      matrix:
        path: ${{ fromJson(needs.detect-changes.outputs.matrix) }}
    steps:
      - name: Build changed component
        run: echo "Building ${{ matrix.path }}"
```

### Monorepo with Path Filtering

```yaml
name: Monorepo CI
on:
  push:
    branches: [main]

jobs:
  detect-changes:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/changed-paths.yml@main
    with:
      filter_paths: '["components/api", "components/web", "components/worker"]'
      path_level: 2

  build:
    needs: detect-changes
    if: needs.detect-changes.outputs.has_changes == 'true'
    runs-on: ubuntu-latest
    strategy:
      matrix:
        path: ${{ fromJson(needs.detect-changes.outputs.matrix) }}
    steps:
      - uses: actions/checkout@v4
      - name: Build
        working-directory: ${{ matrix.path }}
        run: make build
```

### With App Name Generation

```yaml
name: Deploy Changed Apps
on:
  push:
    branches: [main]

jobs:
  detect-changes:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/changed-paths.yml@main
    with:
      filter_paths: '["components/onboarding", "components/transaction", "components/ledger"]'
      path_level: 2
      get_app_name: true
      app_name_prefix: 'midaz'

  deploy:
    needs: detect-changes
    if: needs.detect-changes.outputs.has_changes == 'true'
    runs-on: ubuntu-latest
    strategy:
      matrix:
        app: ${{ fromJson(needs.detect-changes.outputs.matrix) }}
    steps:
      - uses: actions/checkout@v4
      - name: Deploy
        run: |
          echo "Deploying app: ${{ matrix.app.name }}"
          echo "Working directory: ${{ matrix.app.working_dir }}"
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `filter_paths` | JSON array of path prefixes to filter results | No | `''` |
| `path_level` | Limits the path to the first N segments | No | `0` (disabled) |
| `get_app_name` | Output matrix with `name` and `working_dir` fields | No | `false` |
| `app_name_prefix` | Prefix to add to each app name | No | `''` |
| `runner_type` | GitHub runner type | No | `ubuntu-latest` |

## Outputs

| Output | Description |
|--------|-------------|
| `matrix` | JSON array of changed directories (or objects if `get_app_name` is true) |
| `has_changes` | Boolean string (`'true'` or `'false'`) indicating if changes were detected |

## Output Formats

### Default Format (get_app_name: false)

```json
["components/api", "components/web", "libs/common"]
```

### App Name Format (get_app_name: true)

```json
[
  {"name": "api", "working_dir": "components/api"},
  {"name": "web", "working_dir": "components/web"}
]
```

### With Prefix (get_app_name: true, app_name_prefix: "myapp")

```json
[
  {"name": "myapp-api", "working_dir": "components/api"},
  {"name": "myapp-web", "working_dir": "components/web"}
]
```

## Jobs

### get-changed-paths

Detects changed files and extracts unique directories with optional filtering.

**Steps:**
1. Checkout code with full history
2. Compare commits to get changed files
3. Extract and deduplicate directories
4. Apply path level trimming (if configured)
5. Filter by path prefixes (if configured)
6. Generate output matrix

## Example Configurations

### Simple Change Detection

```yaml
jobs:
  changes:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/changed-paths.yml@main
```

### Microservices Monorepo

```yaml
jobs:
  changes:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/changed-paths.yml@main
    with:
      filter_paths: '["services/auth", "services/users", "services/orders", "services/payments"]'
      path_level: 2
      get_app_name: true
      app_name_prefix: 'platform'
```

### Frontend Monorepo

```yaml
jobs:
  changes:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/changed-paths.yml@main
    with:
      filter_paths: '["packages/ui", "packages/utils", "apps/web", "apps/mobile"]'
      path_level: 2
```

### Conditional Job Execution

```yaml
jobs:
  detect:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/changed-paths.yml@main
    with:
      filter_paths: '["src/backend"]'

  backend-tests:
    needs: detect
    if: needs.detect.outputs.has_changes == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: make test-backend
```

## How Path Level Works

The `path_level` input trims paths to the first N segments:

| Original Path | path_level | Result |
|---------------|------------|--------|
| `components/api/src/main.go` | 1 | `components` |
| `components/api/src/main.go` | 2 | `components/api` |
| `components/api/src/main.go` | 3 | `components/api/src` |
| `services/auth/handlers/login.ts` | 2 | `services/auth` |

## Tips

1. **Pin to a version tag**: Use `@v1.0.0` instead of `@main` for production stability
2. **Use `has_changes` output**: Skip downstream jobs when no relevant changes are detected
3. **Path level for consistency**: Use `path_level` to normalize paths to component directories
4. **Filter early**: Use `filter_paths` to focus on relevant directories and reduce noise
5. **Matrix strategy**: Combine with GitHub's matrix strategy for parallel builds

## Requirements

This workflow uses `jq` for JSON processing, which is preinstalled on all GitHub-hosted runners.

For self-hosted runners, ensure `jq` is available:

```bash
# Debian/Ubuntu
sudo apt-get update && sudo apt-get install -y jq

# macOS
brew install jq

# Alpine
apk add jq
```

## Related Workflows

- [Go CI](./go-ci-workflow.md) - Continuous integration for Go projects
- [GitOps Update](./gitops-update-workflow.md) - Update GitOps repository with new image tags

---

**Last Updated:** 2025-11-27
**Version:** 1.0.0
