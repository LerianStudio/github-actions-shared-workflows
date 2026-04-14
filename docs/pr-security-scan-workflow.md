# PR Security Scan Workflow

Reusable workflow for comprehensive security scanning on pull requests. Supports single app repositories and monorepos with automatic detection of changed components.

## Features

- **Secret scanning**: Trivy filesystem scan for exposed secrets (scans only changed component folder)
- **Vulnerability scanning**: Docker image vulnerability detection (optional)
- **CodeQL static analysis**: GitHub CodeQL for semantic code analysis (opt-in via `enable_codeql`)
- **Pre-release version gate**: Blocks dependencies pinned to `-beta` or `-rc` versions (enabled by default)
- **CLI/Non-Docker support**: Skip Docker scanning for projects without Dockerfile via `enable_docker_scan: false`
- **Monorepo support**: Automatic detection of changed components
- **Component-scoped scanning**: Only scans the specific component folder that changed, not entire repo
- **Multiple architectures**: Type 1 and Type 2 monorepo patterns
- **SARIF output**: Security results in standard format
- **Fail-fast on secrets**: Workflow fails if secrets are detected
- **Docker Hub login**: Avoid rate limits during scans
- **Slack notifications**: Automatic success/failure notifications

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
    branches: [develop, release-candidate, main]

jobs:
  security-scan:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-security-scan.yml@v1.0.0
    with:
      runner_type: "blacksmith-4vcpu-ubuntu-2404"
      dockerhub_org: "lerianstudio"
    secrets: inherit
```

### Monorepo Type 1

```yaml
name: PR Security Scan
on:
  pull_request:
    branches: [develop, release-candidate, main]

jobs:
  security-scan:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-security-scan.yml@v1.0.0
    with:
      runner_type: "blacksmith-4vcpu-ubuntu-2404"
      filter_paths: |-
        components/onboarding
        components/transaction
        components/console
      path_level: "2"
      dockerhub_org: "lerianstudio"
    secrets: inherit
```

### Monorepo Type 2

```yaml
name: PR Security Scan
on:
  pull_request:
    branches: [develop, release-candidate, main]

jobs:
  security-scan:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-security-scan.yml@v1.0.0
    with:
      runner_type: "blacksmith-4vcpu-ubuntu-2404"
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
    secrets: inherit
```

### CLI / Non-Docker Projects

For projects without a Dockerfile (e.g., CLI tools), disable Docker scanning to only run filesystem secret scanning:

```yaml
name: PR Security Scan
on:
  pull_request:
    branches: [develop, release-candidate, main]

jobs:
  security-scan:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-security-scan.yml@v1.0.0
    with:
      runner_type: "blacksmith-4vcpu-ubuntu-2404"
      enable_docker_scan: false
    secrets: inherit
```

This will:
- ✅ Run Trivy filesystem secret scanning
- ❌ Skip Docker image build
- ❌ Skip Docker vulnerability scanning
- ❌ Skip Docker Scout analysis

### With CodeQL Analysis

Enable CodeQL for semantic static analysis on top of the standard security scans:

```yaml
name: PR Security Scan
on:
  pull_request:
    branches: [develop, release-candidate, main]

jobs:
  security-scan:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-security-scan.yml@v1.0.0
    with:
      runner_type: "blacksmith-4vcpu-ubuntu-2404"
      enable_codeql: true
      codeql_languages: 'go'
    secrets: inherit
```

This will run all standard scans plus CodeQL analysis scoped to changed paths. Results are posted as a PR comment. To also upload SARIF to the GitHub Security tab, set `codeql_upload_sarif: true` (requires Code Security / GHAS enabled on the repo).

**Supported languages:** `go`, `javascript-typescript`, `actions`, `python`, `java-kotlin`, `csharp`, `ruby`, `swift`, `cpp`

### With Pre-release Version Gate

Pre-release checks are enabled by default. To disable:

```yaml
jobs:
  security-scan:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-security-scan.yml@v1.0.0
    with:
      enable_prerelease_check: false
    secrets: inherit
```

When enabled, the workflow scans `go.mod`, `package.json`, and `Dockerfile` for unstable version pins (`-alpha`, `-beta`, `-rc`, `-dev`, etc.). On branches listed in `prerelease_block_branches` (default: `release-candidate,main`) the PR is blocked. On other branches (e.g., `develop`) findings are reported as warnings only.

## Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `runner_type` | string | `blacksmith-4vcpu-ubuntu-2404` | GitHub runner type |
| `filter_paths` | string | - | Paths to monitor (newline separated). If empty, treats as single app |
| `path_level` | string | `2` | Directory depth level to extract app name (monorepo only) |
| `monorepo_type` | string | `type1` | Monorepo type: `type1` or `type2` |
| `frontend_folder` | string | `frontend` | Frontend folder name for type2 monorepos |
| `dockerhub_org` | string | `lerianstudio` | DockerHub organization name |
| `docker_registry` | string | `docker.io` | Docker registry URL |
| `dockerfile_name` | string | `Dockerfile` | Name of the Dockerfile |
| `enable_docker_scan` | boolean | `true` | Enable Docker image build and vulnerability scanning. Set to `false` for projects without Dockerfile (e.g., CLI tools) |
| `enable_health_score` | boolean | `true` | Enable Docker Hub Health Score compliance checks (non-root user, CVEs, licenses) |
| `enable_codeql` | boolean | `false` | Enable CodeQL static analysis. Requires `codeql_languages` to be set |
| `codeql_languages` | string | `''` | Languages to analyze with CodeQL (comma-separated, e.g., `go`, `javascript-typescript`, `actions`) |
| `codeql_fail_on_findings` | boolean | `true` | Fail the workflow when CodeQL detects security issues |
| `codeql_upload_sarif` | boolean | `false` | Upload CodeQL SARIF results to the GitHub Security tab. Requires Code Security (GHAS) enabled on the repo |
| `enable_prerelease_check` | boolean | `true` | Block dependencies pinned to pre-release versions (`-beta`, `-rc`) |
| `prerelease_block_branches` | string | `release-candidate,main` | Comma-separated PR target branches where pre-release versions cause a hard failure. On other branches, findings are reported as warnings only |

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

1. **Docker Login**: Authenticate to registry (avoids rate limits)
2. **Checkout Repository**: Clone the code
3. **Setup Docker Buildx**: Enable multi-platform builds *(skipped if `enable_docker_scan: false`)*
4. **Trivy Filesystem Scan**: Scan filesystem for secrets and vulnerabilities
5. **Build Docker Image**: Build image for vulnerability scanning *(skipped if `enable_docker_scan: false`)*
6. **Trivy Image Scan**: Scan image for vulnerabilities and licenses *(skipped if `enable_docker_scan: false`)*
7. **Dockerfile Compliance Checks**: Non-root user and health score checks *(skipped unless `enable_health_score: true` AND `enable_docker_scan: true`)*
8. **Pre-release Version Check**: Scan for `-beta`/`-rc` version pins *(skipped if `enable_prerelease_check: false`)*
9. **Post Security Scan Results**: PR comment with consolidated findings

> **Note**: When `enable_docker_scan: false`, only filesystem scanning and pre-release checks run.

### Job 3: codeql_scan *(optional)*

Runs when `enable_codeql: true` and `codeql_languages` is set:

1. **Checkout Repository**: Clone the code
2. **Extract Changed Paths**: Derive scoped paths from the component matrix
3. **Generate CodeQL Config**: Scope analysis to changed paths
4. **Initialize CodeQL**: Set up CodeQL with configured languages and query suite
5. **Autobuild**: Automatically build the project for compiled languages
6. **Perform CodeQL Analysis**: Run semantic analysis and upload SARIF
7. **Post CodeQL Results**: PR comment with findings table and security gate

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

### CodeQL Analysis

**What it does**: Runs GitHub CodeQL semantic analysis for security vulnerabilities and code quality issues

**Scope**: Automatically scoped to changed paths in the PR (via `codeql-config` composite)

**Query suite**: `security-extended` (default) — covers OWASP Top 10, CWE Top 25, and more

**Exit behavior**: Configurable via `codeql_fail_on_findings` (default: fails on findings)

### Pre-release Version Gate

**What it does**: Scans `go.mod`, `package.json`, and `Dockerfile` for unstable version pins

**Pattern matched**: `X.Y.Z-<letter...>` for Go/npm (any pre-release suffix starting with a letter). For Docker, only known pre-release prefixes: `-alpha`, `-beta`, `-rc`, `-dev`, `-preview`, `-canary`, `-snapshot`, `-nightly`. Stable Docker variants like `-slim`, `-alpine`, `-bookworm` are allowed.

**Exit behavior**: `exit-code: 1` on branches listed in `prerelease_block_branches` (default: `release-candidate,main`). On other branches (e.g., `develop`), findings are reported as warnings only.

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
    branches: [develop, release-candidate, main]
```

### 2. Use Blacksmith Runners for Better Performance

```yaml
with:
  runner_type: "blacksmith-4vcpu-ubuntu-2404"
```

### 3. Use secrets: inherit for Simplicity

```yaml
secrets: inherit
```

This passes all repository secrets to the workflow automatically.

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
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-security-scan.yml@v1.0.0
  with:
    dockerhub_org: "mycompany"
    docker_registry: "ghcr.io"
  secrets: inherit
```

> **Note**: For GitHub Container Registry (ghcr.io), ensure `DOCKER_USERNAME` and `DOCKER_PASSWORD` secrets are configured appropriately.

### Monorepo Type 1 with Multiple Components

```yaml
security-scan:
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-security-scan.yml@v1.0.0
  with:
    runner_type: "blacksmith-4vcpu-ubuntu-2404"
    filter_paths: |-
      services/auth
      services/payment
      services/notification
      services/user
    path_level: "2"
    monorepo_type: "type1"
  secrets: inherit
```

### Monorepo Type 2 with Custom Frontend Folder

```yaml
security-scan:
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-security-scan.yml@v1.0.0
  with:
    runner_type: "blacksmith-4vcpu-ubuntu-2404"
    filter_paths: |-
      web
      api
      cmd
      internal
      .
    path_level: "1"
    monorepo_type: "type2"
    frontend_folder: "web"
  secrets: inherit
```

### Complete PR Workflow

```yaml
name: Pull Request Checks
on:
  pull_request:
    branches: [develop, release-candidate, main]

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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-security-scan.yml@v1.0.0
    with:
      runner_type: "blacksmith-4vcpu-ubuntu-2404"
      filter_paths: |-
        components/onboarding
        components/transaction
      path_level: "2"
    secrets: inherit
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

Uploaded to GitHub Security tab via CodeQL when `enable_codeql` is enabled.

## Related Workflows

- [GitOps Update](gitops-update-workflow.md) - Update deployments after security checks pass
- [API Dog E2E Tests](api-dog-e2e-tests-workflow.md) - Run E2E tests after security validation
- [Release Workflow](release-workflow.md) - Create releases after all checks pass
