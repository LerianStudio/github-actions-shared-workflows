# GitHub Actions Shared Workflows

Centralized repository for reusable GitHub Actions workflows used across the Lerian organization. Simplifies CI/CD management, promotes consistency, and reduces duplication by sharing standardized pipeline configurations.

## Available Workflows

### Detect Changes (Monorepo Change Detection)

Intelligent change detection workflow for monorepos. Analyzes git diff to determine which apps were modified, considering direct changes, shared library changes, and ignore patterns defined in `apps-config.yml`.

**Usage:**

```yaml
name: PR CI/CD
on:
  pull_request:
    branches: [main, develop, release-candidate]

jobs:
  detect-changes:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/detect-changes.yml@main
    with:
      config_path: ".github/apps-config.yml"

  ci-matrix:
    needs: detect-changes
    if: needs.detect-changes.outputs.has_changes == 'true'
    strategy:
      matrix: ${{ fromJson(needs.detect-changes.outputs.changed_apps_matrix) }}
    runs-on: ubuntu-latest
    steps:
      - name: Run CI for ${{ matrix.app }}
        run: echo "Running CI for ${{ matrix.app }} at ${{ matrix.path }}"
```

**Inputs:**

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `config_path` | Path to apps-config.yml | No | `.github/apps-config.yml` |
| `base_ref` | Base reference for comparison | No | PR base or `HEAD~1` |

**Outputs:**

| Output | Type | Description |
|--------|------|-------------|
| `changed_apps` | JSON array | List of changed app names: `["flowker", "tracer"]` |
| `changed_apps_matrix` | JSON object | Matrix with app metadata for strategy |
| `all_apps` | JSON array | All enabled apps from config |
| `has_changes` | boolean | `true` if any apps changed |

**Features:**

- ✅ Intelligent path-based detection
- ✅ Shared library awareness (`pkg/**` affects all apps)
- ✅ CI/CD change awareness (`.github/workflows/**` affects all)
- ✅ Configurable ignore patterns (`*.md`, `docs/**`, etc.)
- ✅ Component-level granularity
- ✅ Matrix output ready for `strategy.matrix`
- ✅ Detailed logging for debugging

**Example Output:**

```json
{
  "changed_apps": ["flowker", "tracer"],
  "changed_apps_matrix": {
    "include": [
      {
        "app": "flowker",
        "path": "apps/flowker",
        "type": "backend",
        "has_go": true,
        "has_node": false
      },
      {
        "app": "tracer",
        "path": "apps/tracer",
        "type": "backend",
        "has_go": true,
        "has_node": false
      }
    ]
  },
  "has_changes": true
}
```

---

### API Dog E2E Tests

Automated API testing workflow using Apidog CLI that runs test scenarios and generates comprehensive reports. Supports both manual environment specification and automatic environment detection based on git tags (beta/rc).

**Usage (Manual Environment):**

```yaml
name: API Testing
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  api-tests:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/api-dog-e2e-tests.yml@main
    with:
      environment_id: "4770599"
      test_iterations: "1"
      output_formats: "html,cli"
      node_version: "20"
      runner_type: "ubuntu-latest"
    secrets:
      test_scenario_id: ${{ secrets.APIDOG_TEST_SCENARIO_ID }}
      apidog_access_token: ${{ secrets.APIDOG_ACCESS_TOKEN }}
```

**Usage (Auto-detect Environment from Tag):**

```yaml
name: API Testing on Release
on:
  push:
    tags:
      - '*-beta.*'
      - '*-rc.*'

jobs:
  api-tests:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/api-dog-e2e-tests.yml@main
    with:
      auto_detect_environment: true
    secrets:
      test_scenario_id: ${{ secrets.MIDAZ_APIDOG_TEST_SCENARIO_ID }}
      apidog_access_token: ${{ secrets.APIDOG_ACCESS_TOKEN }}
      dev_environment_id: ${{ secrets.MIDAZ_APIDOG_DEV_ENVIRONMENT_ID }}
      stg_environment_id: ${{ secrets.MIDAZ_APIDOG_STG_ENVIRONMENT_ID }}
```

**Inputs:**

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `environment_id` | Apidog environment ID (ignored if auto_detect_environment is true) | No | - |
| `auto_detect_environment` | Enable automatic environment detection from tag (beta/rc) | No | `false` |
| `test_iterations` | Number of test iterations | No | `"1"` |
| `output_formats` | Report formats (comma-separated) | No | `"html,cli"` |
| `node_version` | Node.js version to use | No | `"20"` |
| `runner_type` | GitHub runner type | No | `"firmino-lxc-runners"` |

**Secrets:**

| Secret | Description | Required |
|--------|-------------|----------|
| `test_scenario_id` | Apidog test scenario ID | Yes |
| `apidog_access_token` | Apidog access token for authentication | Yes |
| `dev_environment_id` | Apidog dev environment ID (for beta tags) | No* |
| `stg_environment_id` | Apidog staging environment ID (for rc tags) | No* |

*Required when `auto_detect_environment` is `true`

**Features:**

- ✅ Automated API test execution with Apidog CLI
- ✅ Multiple output formats (HTML, CLI)
- ✅ Configurable test iterations
- ✅ Artifact upload with 30-day retention
- ✅ Test results summary in GitHub Actions
- ✅ Support for both GitHub-hosted and self-hosted runners
- ✅ Automatic environment detection from git tags (beta/rc)
- ✅ Automatic CLI cleanup after test execution

### PR Security Scan

Reusable workflow that handles security scanning for pull requests. Supports both single app repositories and monorepos with two different architectures:
- **Single App Mode**: Scans entire repository when `filter_paths` is not provided
- **Monorepo Type 1**: Components in separate folders with individual Dockerfiles
- **Monorepo Type 2**: Backend in root with `./Dockerfile`, frontend in folder with `folder/Dockerfile`

Workflow file: `.github/workflows/pr-security-scan.yml`

**Usage (Single App):**

```yaml
name: PR Security Scan
on:
  pull_request:
    branches: [ main, develop ]

jobs:
  security-scan:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-security-scan.yml@main
    with:
      runner_type: "firmino-lxc-runners"
      dockerhub_org: "lerianstudio"
    secrets:
      manage_token: ${{ secrets.MANAGE_TOKEN }}
      docker_username: ${{ secrets.DOCKER_USERNAME }}
      docker_password: ${{ secrets.DOCKER_PASSWORD }}
```

**Usage (Monorepo Type 1):**

```yaml
name: PR Security Scan
on:
  pull_request:
    branches: [ main, develop ]

jobs:
  security-scan:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-security-scan.yml@main
    with:
      runner_type: "firmino-lxc-runners"
      filter_paths: |-
        components/onboarding
        components/transaction
        components/console
      path_level: "2"
      dockerhub_org: "lerianstudio"
    secrets:
      manage_token: ${{ secrets.MANAGE_TOKEN }}
      docker_username: ${{ secrets.DOCKER_USERNAME }}
      docker_password: ${{ secrets.DOCKER_PASSWORD }}
```

**Usage (Monorepo Type 2):**

```yaml
name: PR Security Scan
on:
  pull_request:
    branches: [ main, develop ]

jobs:
  security-scan:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-security-scan.yml@main
    with:
      runner_type: "firmino-lxc-runners"
      filter_paths: |-
        frontend
        cmd
        internal
        api
        pkg
        .
      path_level: "1"
      monorepo_type: "type2"
      frontend_folder: "frontend"
      dockerhub_org: "lerianstudio"
    secrets:
      manage_token: ${{ secrets.MANAGE_TOKEN }}
      docker_username: ${{ secrets.DOCKER_USERNAME }}
      docker_password: ${{ secrets.DOCKER_PASSWORD }}
```

**Inputs:**

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `runner_type` | GitHub runner type to use | No | `"ubuntu-latest"` |
| `filter_paths` | Paths to monitor for changes (newline separated). If not provided, treats as single app repo | No | - |
| `path_level` | Directory depth level to extract app name (only used for monorepo) | No | `"2"` |
| `monorepo_type` | Type of monorepo: "type1" (components in folders) or "type2" (backend in root, frontend in folder) | No | `"type1"` |
| `frontend_folder` | Name of the frontend folder for type2 monorepos | No | `"frontend"` |
| `dockerhub_org` | DockerHub organization name | No | `"lerianstudio"` |
| `docker_registry` | Docker registry URL | No | `"docker.io"` |

**Secrets:**

| Secret | Description | Required |
|--------|-------------|----------|
| `manage_token` | GitHub token for accessing private repositories during Docker build | No |
| `docker_username` | Docker registry username | Yes |
| `docker_password` | Docker registry password | Yes |

**Required permissions:**

```yaml
permissions:
  id-token: write       # Required for OIDC authentication
  contents: read        # Required to checkout the repository
  pull-requests: write  # Allows commenting on PRs
  security-events: write # Required for security scanning
```

**Features:**

- ✅ Trivy Secret Scan on repository filesystem (fails on secrets found)
- ✅ Trivy Vulnerability Scan on Docker images (CRITICAL, HIGH severity)
- ✅ SARIF output generation for both scans
- ✅ Supports single app and monorepo architectures
- ✅ Automatic detection of changed components in monorepos
- ✅ Type 2 monorepo support with backend/frontend separation
- ✅ Ignores `.github` and `.githooks` folders in Type 2 monorepos
- ✅ Sequential scanning with `max-parallel: 1`
- ✅ Continues on failure with `fail-fast: false`

**What it does:**

1. **prepare_matrix** job: Detects changed paths and prepares matrix of components to scan
   - Single app: Creates matrix with repository name and root directory
   - Type 1 monorepo: Uses changed paths directly
   - Type 2 monorepo: Consolidates backend changes to root, keeps frontend separate

2. **security_scan** job: For each component in the matrix:
   - Runs Trivy Secret Scan (table + SARIF output) - **fails workflow if secrets found**
   - Builds Docker image for scanning
   - Runs Trivy Vulnerability Scan (table + SARIF output) - informative only
   - Generates reports for both scans

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
