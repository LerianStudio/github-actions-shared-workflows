# PR Security Scan Workflow

Reusable workflow for comprehensive security scanning on pull requests. Supports single app repositories and monorepos with automatic detection of changed components.

## Features

- **Secret scanning**: Trivy filesystem scan for exposed secrets
- **Vulnerability scanning**: Docker image vulnerability detection
- **Monorepo support**: Automatic detection of changed components
- **Multiple architectures**: Type 1 and Type 2 monorepo patterns
- **SARIF output**: Security results in standard format
- **Fail-fast on secrets**: Workflow fails if secrets are detected
- **Docker Hub login**: Avoid rate limits during scans

## Architecture Support

### Single App Mode
Scans entire repository when `filter_paths` is not provided.

### Monorepo Type 1
Components in separate folders with individual Dockerfiles:
```
project/
├── components/
│   ├── onboarding/
│   │   └── Dockerfile
│   ├── transaction/
│   │   └── Dockerfile
│   └── console/
│       └── Dockerfile
```

### Monorepo Type 2
Backend in root with frontend in separate folder:
```
project/
├── Dockerfile          # Backend
├── api/
├── cmd/
├── internal/
└── frontend/
    └── Dockerfile      # Frontend
```

## Usage

### Single App

```yaml
name: PR Security Scan
on:
  pull_request:
    branches: [main, develop]

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

### Monorepo Type 1

```yaml
name: PR Security Scan
on:
  pull_request:
    branches: [main, develop]

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

### Monorepo Type 2

```yaml
name: PR Security Scan
on:
  pull_request:
    branches: [main, develop]

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

## Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `runner_type` | string | `ubuntu-latest` | GitHub runner type |
| `filter_paths` | string | - | Paths to monitor (newline separated). If empty, treats as single app |
| `path_level` | string | `2` | Directory depth level to extract app name (monorepo only) |
| `monorepo_type` | string | `type1` | Monorepo type: `type1` or `type2` |
| `frontend_folder` | string | `frontend` | Frontend folder name for type2 monorepos |
| `dockerhub_org` | string | `lerianstudio` | DockerHub organization name |
| `docker_registry` | string | `docker.io` | Docker registry URL |

## Secrets

### Required Secrets

| Secret | Description |
|--------|-------------|
| `docker_username` | Docker registry username |
| `docker_password` | Docker registry password |

### Optional Secrets

| Secret | Description | Required When |
|--------|-------------|---------------|
| `manage_token` | GitHub token for private repositories | Building images that need private repo access |

## Required Permissions

```yaml
permissions:
  id-token: write       # Required for OIDC authentication
  contents: read        # Required to checkout the repository
  pull-requests: write  # Allows commenting on PRs
  security-events: write # Required for security scanning
```

## Workflow Steps

### Job 1: prepare_matrix

1. **Docker Login**: Authenticate to avoid rate limits
2. **Get Changed Paths**: Detect which components changed (monorepo only)
3. **Set Matrix**: Build matrix of components to scan

### Job 2: security_scan

For each component in the matrix:

1. **Docker Login**: Authenticate to registry
2. **Checkout Repository**: Clone the code
3. **Setup Docker Buildx**: Enable multi-platform builds
4. **Trivy Secret Scan (Table)**: Scan filesystem for secrets - **fails on detection**
5. **Trivy Secret Scan (SARIF)**: Generate SARIF report
6. **Build Docker Image**: Build image for vulnerability scanning
7. **Trivy Vulnerability Scan (Table)**: Scan image for vulnerabilities
8. **Trivy Vulnerability Scan (SARIF)**: Generate SARIF report

## Security Scans

### Secret Scan

**What it does**: Scans repository filesystem for exposed secrets (API keys, tokens, passwords)

**Severity**: CRITICAL - workflow fails if secrets are found

**Skipped directories**:
- `.git`
- `node_modules`
- `dist`
- `build`
- `.next`
- `coverage`
- `vendor`

**Exit behavior**: `exit-code: 1` (fails workflow)

### Vulnerability Scan

**What it does**: Scans Docker image for known vulnerabilities

**Severity levels**: CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN

**Vulnerability types**:
- OS packages
- Application libraries

**Exit behavior**: `exit-code: 0` (informative only, doesn't fail workflow)

## Monorepo Type 2 Behavior

### Backend Changes

Any changes to backend folders (`api`, `cmd`, `internal`, `pkg`, `.`) are consolidated to root:

```json
{
  "name": "repository-name",
  "working_dir": "."
}
```

### Frontend Changes

Frontend changes are kept separate:

```json
{
  "name": "repository-name-frontend",
  "working_dir": "frontend"
}
```

### Ignored Folders

Changes to `.github` and `.githooks` are ignored in Type 2 monorepos.

## Best Practices

### 1. Always Enable for Pull Requests

```yaml
on:
  pull_request:
    branches: [main, develop, release-candidate]
```

### 2. Use Self-hosted Runners for Better Performance

```yaml
with:
  runner_type: "firmino-lxc-runners"
```

### 3. Provide GitHub Token for Private Dependencies

```yaml
secrets:
  manage_token: ${{ secrets.MANAGE_TOKEN }}
```

Required when Dockerfile needs access to private repositories.

### 4. Configure Path Level Correctly

**Type 1 Monorepo** (components in folders):
```yaml
with:
  path_level: "2"  # components/onboarding → onboarding
```

**Type 2 Monorepo** (backend in root):
```yaml
with:
  path_level: "1"  # api → api, frontend → frontend
```

### 5. Specify All Relevant Paths

Include all directories that should trigger scans:

```yaml
with:
  filter_paths: |-
    api
    cmd
    internal
    pkg
    frontend
    .
```

## Troubleshooting

### Scan Not Running

**Issue**: Security scan doesn't run on PR

**Solutions**:
1. Check if changed paths match `filter_paths`
2. Verify PR targets correct branch
3. Check workflow permissions

### Docker Build Fails

**Issue**: Cannot build Docker image

**Solutions**:
1. Provide `manage_token` for private dependencies
2. Check Dockerfile path
3. Verify Docker registry credentials

### Rate Limit Errors

**Issue**: Docker Hub rate limit (429 errors)

**Solution**: Workflow includes automatic Docker login to avoid rate limits. Ensure `docker_username` and `docker_password` secrets are set.

### Secret Scan False Positives

**Issue**: Scan detects test secrets or examples

**Solutions**:
1. Move test secrets to `.env.example` files
2. Use placeholder values in documentation
3. Add comments to indicate test data

### Multiple Components Scanned

**Issue**: All components scanned instead of only changed ones

**Solution**: Verify `filter_paths` configuration matches your repository structure.

## Examples

### Single App with Custom Registry

```yaml
security-scan:
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-security-scan.yml@main
  with:
    dockerhub_org: "mycompany"
    docker_registry: "ghcr.io"
  secrets:
    docker_username: ${{ github.actor }}
    docker_password: ${{ secrets.GITHUB_TOKEN }}
```

### Monorepo Type 1 with Multiple Components

```yaml
security-scan:
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-security-scan.yml@main
  with:
    filter_paths: |-
      services/auth
      services/payment
      services/notification
      services/user
    path_level: "2"
    monorepo_type: "type1"
  secrets:
    manage_token: ${{ secrets.MANAGE_TOKEN }}
    docker_username: ${{ secrets.DOCKER_USERNAME }}
    docker_password: ${{ secrets.DOCKER_PASSWORD }}
```

### Monorepo Type 2 with Custom Frontend Folder

```yaml
security-scan:
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-security-scan.yml@main
  with:
    filter_paths: |-
      web
      api
      cmd
      internal
      .
    path_level: "1"
    monorepo_type: "type2"
    frontend_folder: "web"
  secrets:
    manage_token: ${{ secrets.MANAGE_TOKEN }}
    docker_username: ${{ secrets.DOCKER_USERNAME }}
    docker_password: ${{ secrets.DOCKER_PASSWORD }}
```

### Complete PR Workflow

```yaml
name: Pull Request Checks
on:
  pull_request:
    branches: [main, develop]

permissions:
  id-token: write
  contents: read
  pull-requests: write
  security-events: write

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run linters
        run: make lint

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: make test

  security-scan:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-security-scan.yml@main
    with:
      runner_type: "firmino-lxc-runners"
      filter_paths: |-
        components/onboarding
        components/transaction
      path_level: "2"
    secrets:
      manage_token: ${{ secrets.MANAGE_TOKEN }}
      docker_username: ${{ secrets.DOCKER_USERNAME }}
      docker_password: ${{ secrets.DOCKER_PASSWORD }}
```

## Scan Results

### Table Output

Displayed in workflow logs for quick review:

```
┌─────────────────────────────────────────────────────────────┐
│ Trivy Secret Scan Results                                   │
├─────────────────────────────────────────────────────────────┤
│ No secrets found                                            │
└─────────────────────────────────────────────────────────────┘
```

### SARIF Output

Generated for each scan type:
- `trivy-secret-scan-repo-{app-name}.sarif`
- `trivy-vulnerability-scan-docker-{app-name}.sarif`

Can be uploaded to GitHub Security tab (currently commented out in workflow).

## Related Workflows

- [GitOps Update](gitops-update-workflow.md) - Update deployments after security checks pass
- [API Dog E2E Tests](api-dog-e2e-tests-workflow.md) - Run E2E tests after security validation
- [Release Workflow](release-workflow.md) - Create releases after all checks pass
