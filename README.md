# GitHub Actions Shared Workflows

Centralized repository for reusable GitHub Actions workflows used across the Lerian organization.

## Available Workflows

### 1. [Go CI](docs/go-ci-workflow.md)
Multi-version Go continuous integration with testing, linting, and optional cross-platform builds.

**Key Features**: Multi-version testing, golangci-lint, cross-platform builds, coverage comments

### 2. [Go Security](docs/go-security-workflow.md)
Comprehensive security scanning for Go projects with 8 security tools.

**Key Features**: Gosec, govulncheck, Nancy, Trivy, TruffleHog, license checks, SBOM generation

### 3. [Go Release](docs/go-release-workflow.md)
Automated release creation using GoReleaser with optional Docker and Homebrew publishing.

**Key Features**: GoReleaser automation, multi-platform builds, Docker images, Homebrew formulas

### 4. [GitOps Update](docs/gitops-update-workflow.md)
Update GitOps repository with new image tags across multiple environments.

**Key Features**: Multi-environment support, automatic environment detection, ArgoCD sync

### 5. [API Dog E2E Tests](docs/api-dog-e2e-tests-workflow.md)
Automated API testing using Apidog CLI with comprehensive reporting.

**Key Features**: Auto environment detection, multiple output formats, configurable iterations

### 6. [PR Validation](docs/pr-validation-workflow.md)
Comprehensive pull request validation enforcing best practices and coding standards.

**Key Features**: Semantic PR titles, size tracking, auto-labeling, changelog checks, source branch validation

### 7. [PR Security Scan](docs/pr-security-scan-workflow.md)
Comprehensive security scanning for pull requests with Trivy.

**Key Features**: Secret scanning, vulnerability scanning, monorepo support, component-scoped scanning

### 8. [Release Workflow](docs/release-workflow.md)
Semantic versioning and automated release management with GPG signing.

**Key Features**: Semantic versioning, GPG signing, hotfix support

### 9. [Changed Paths](docs/changed-paths-workflow.md)
Detect changed paths between commits for monorepo CI/CD optimization.

**Key Features**: Path filtering, path level trimming, app name generation, matrix strategy support

### 10. [Go PR Analysis](docs/go-pr-analysis-workflow.md)
Comprehensive Go PR analysis for monorepos with change detection, linting, security, testing, and coverage.

**Key Features**: Change detection, matrix execution, GolangCI-Lint, GoSec, coverage checks, private module support

### 11. [Build](docs/build-workflow.md)
Build and push Docker images with monorepo support and multi-platform builds.

**Key Features**: Monorepo support, multi-registry (DockerHub/GHCR), smart platform builds, GitOps artifacts

### 12. [Slack Notify](docs/slack-notify-workflow.md)
Send Slack notifications from workflows with rich formatting and status-based colors.

**Key Features**: Rich formatting, status colors, graceful degradation, PR support

### 13. [Frontend PR Analysis](docs/frontend-pr-analysis-workflow.md)
Comprehensive Frontend/Node.js PR analysis for monorepos with change detection, linting, type checking, security, testing, and coverage.

**Key Features**: Change detection, matrix execution, ESLint, TypeScript, npm audit, coverage checks, npm/yarn/pnpm support

### 14. [GPT Changelog](docs/gptchangelog-workflow.md)
AI-powered changelog generation using OpenRouter API (GPT-4o) with consolidated output.

**Key Features**: AI commit analysis, consolidated changelog, monorepo support, GitHub Release integration, GPG signing

## Documentation

Individual workflow documentation is available in the [`docs/`](docs/) directory.

## Quick Start

> **Tip:** Pin to a specific release tag in production (e.g. `@v1.2.3`) instead of `@main` for stability. See [versioning](#versioning) for details.

```yaml
# Example: Complete CI/CD Pipeline
jobs:
  security_scan:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-security-scan.yml@v1.2.3

  release:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/release.yml@v1.2.3

  update_gitops:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@v1.2.3

  e2e_tests:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/api-dog-e2e-tests.yml@v1.2.3
```

See the [`docs/`](docs/) directory for complete examples and configuration options for each workflow.

## Versioning

This repository uses [Semantic Versioning](https://semver.org/) with automated releases via [semantic-release](https://github.com/semantic-release/semantic-release).

**Branches:**
- `develop` — Development branch; merges here publish a beta pre-release (`v1.2.3-beta.1`)
- `main` — Production branch; merges here publish a stable release (`v1.2.3`)

**Commit types and version impact:**

| Type | Version bump |
|---|---|
| `feat`, `perf`, `refactor`, `build` | Minor (`1.x.0`) |
| `fix`, `docs`, `chore`, `ci`, `test` | Patch (`1.0.x`) |
| `BREAKING CHANGE` (in footer) | Major (`x.0.0`) |

Follow [Conventional Commits](https://www.conventionalcommits.org/) format. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full reference.

## Contributing

This repository is open to contributions. Please read [CONTRIBUTING.md](CONTRIBUTING.md) for branch strategy, commit conventions, and the pull request process.

## Security

To report a security vulnerability, please follow the process described in [SECURITY.md](SECURITY.md). Do not open a public issue.

## License

This project is licensed under the Apache License 2.0 — see the [LICENSE](LICENSE) file for details.
