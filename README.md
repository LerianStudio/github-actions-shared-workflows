# GitHub Actions Shared Workflows

Centralized repository for reusable GitHub Actions workflows used across the Lerian organization.

## 📚 Available Workflows

### 1. [GitOps Update](docs/gitops-update-workflow.md)
Update GitOps repository with new image tags across multiple environments.

**Key Features**: Multi-environment support, automatic environment detection, ArgoCD sync

### 2. [API Dog E2E Tests](docs/api-dog-e2e-tests-workflow.md)
Automated API testing using Apidog CLI with comprehensive reporting.

**Key Features**: Auto environment detection, multiple output formats, configurable iterations

### 3. [PR Security Scan](docs/pr-security-scan-workflow.md)
Comprehensive security scanning for pull requests with Trivy.

**Key Features**: Secret scanning, vulnerability scanning, monorepo support

### 4. [Release Workflow](docs/release-workflow.md)
Semantic versioning and automated release management with GPG signing.

**Key Features**: Semantic versioning, GPG signing, hotfix support

## 📖 Documentation

**[Complete Documentation →](docs/README.md)**

Comprehensive guides with examples, best practices, and troubleshooting for all workflows.

## 🚀 Quick Start

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

## 🔄 Versioning

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

## 🤝 Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
