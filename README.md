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
Comprehensive Go PR analysis for monorepos with change detection, linting, security, testing, and coverage. Replaces standalone go-coverage-check and go-unit-tests workflows.

**Key Features**: Change detection, matrix execution, GolangCI-Lint, GoSec, coverage checks, private module support

### 11. [Build](docs/build-workflow.md)
Build and push Docker images with monorepo support and multi-platform builds.

**Key Features**: Monorepo support, multi-registry (DockerHub/GHCR), smart platform builds, GitOps artifacts

### 12. [Slack Notify](docs/slack-notify-workflow.md)
Send Slack notifications from workflows with rich formatting and status-based colors.

**Key Features**: Rich formatting, status colors, graceful degradation, PR support

## Documentation

**[Complete Documentation →](docs/README.md)**

Comprehensive guides with examples, best practices, and troubleshooting for all workflows.

## Quick Start

```yaml
# Example: Complete CI/CD Pipeline
jobs:
  security_scan:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-security-scan.yml@main

  release:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/release.yml@main

  update_gitops:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@main

  e2e_tests:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/api-dog-e2e-tests.yml@main
```

See [documentation](docs/README.md) for complete examples and configuration options.

## Versioning

This repository uses [Semantic Versioning](https://semver.org/) with automated releases via [semantic-release](https://github.com/semantic-release/semantic-release).

**Release Process:**
- Commits to `develop` → Beta releases (`v1.2.3-beta.1`)
- Commits to `release-candidate` → RC releases (`v1.2.3-rc.1`)
- Commits to `main` → Production releases (`v1.2.3`)

**Commit Message Format:**
Follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` - New feature (minor version bump)
- `fix:` - Bug fix (patch version bump)
- `BREAKING CHANGE:` - Breaking change (major version bump)
- `docs:`, `chore:`, `ci:`, `test:` - No version bump

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
