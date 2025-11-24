# Go Security Workflow

Comprehensive security scanning workflow for Go projects. Includes vulnerability detection, secret scanning, license compliance checks, and SBOM generation using industry-standard tools.

## Features

- **Gosec** - Go security scanner with SARIF upload
- **govulncheck** - Official Go vulnerability database
- **Nancy** - Sonatype dependency vulnerability scanner
- **Trivy** - Filesystem security scanner
- **TruffleHog** - Secret detection
- **go-licenses** - License compliance checking
- **SBOM** - Software Bill of Materials generation (SPDX format)
- **Dependency Review** - GitHub-native PR dependency check
- SARIF uploads to GitHub Security tab
- Configurable severity levels and scanners
- Security summary with all scan results

## Usage

### Basic Usage

```yaml
name: Security
on:
  push:
    branches: [develop, release-candidate, main]
  pull_request:
    branches: [develop, release-candidate, main]
  schedule:
    - cron: '0 0 * * 1'  # Weekly on Mondays
  workflow_dispatch:

jobs:
  security:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-security.yml@main
```

### Custom Configuration

```yaml
name: Security
on: [push, pull_request]

jobs:
  security:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-security.yml@main
    with:
      go_version: '1.23'
      enable_gosec: true
      enable_govulncheck: true
      enable_trivy: true
      enable_secret_scan: true
      trivy_severity: 'CRITICAL,HIGH'
      upload_sarif: true
      fail_on_security_issues: true
```

### Selective Scanning

```yaml
name: Security
on: [push, pull_request]

jobs:
  security:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-security.yml@main
    with:
      # Only run critical scanners
      enable_gosec: true
      enable_govulncheck: true
      enable_trivy: true
      # Skip less critical scanners
      enable_nancy: false
      enable_license_check: false
      enable_sbom: false
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `runner_type` | GitHub runner type to use | No | `ubuntu-latest` |
| `go_version` | Go version for security scanning | No | `1.23` |
| `enable_dependency_review` | Enable GitHub dependency review (PR only) | No | `true` |
| `enable_gosec` | Enable Gosec security scanner | No | `true` |
| `enable_govulncheck` | Enable Go vulnerability database check | No | `true` |
| `enable_nancy` | Enable Nancy dependency scanner | No | `true` |
| `enable_trivy` | Enable Trivy filesystem scanner | No | `true` |
| `enable_secret_scan` | Enable TruffleHog secret scanning | No | `true` |
| `enable_license_check` | Enable go-licenses compliance check | No | `true` |
| `enable_sbom` | Enable SBOM generation | No | `true` |
| `trivy_severity` | Trivy severity levels (comma-separated) | No | `CRITICAL,HIGH` |
| `license_disallowed_types` | Disallowed license types (comma-separated) | No | `forbidden,restricted` |
| `upload_sarif` | Upload SARIF to GitHub Security tab | No | `true` |
| `fail_on_security_issues` | Fail workflow on critical issues | No | `true` |

## Secrets

No secrets required. All scanners use public databases and GitHub's built-in token.

## Jobs

### dependency-review
GitHub-native dependency review for pull requests.

### gosec
Go security scanner that finds security issues in Go code.

### govulncheck
Official Go vulnerability database scanner.

### nancy
Sonatype Nancy dependency vulnerability scanner.

### trivy
Aqua Security Trivy filesystem scanner.

### secret-scan
TruffleHog secret detection scanner.

### license-check
go-licenses compliance checker.

### sbom
Software Bill of Materials generation.

### security-summary
Aggregate summary of all security scans.

## Example Configurations

### Minimal (All Defaults)

```yaml
jobs:
  security:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-security.yml@main
```

### Critical Scanners Only

```yaml
jobs:
  security:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-security.yml@main
    with:
      enable_gosec: true
      enable_govulncheck: true
      enable_secret_scan: true
      enable_nancy: false
      enable_trivy: false
      enable_license_check: false
      enable_sbom: false
```

### Don't Fail on Issues (Report Only)

```yaml
jobs:
  security:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-security.yml@main
    with:
      fail_on_security_issues: false
```

## Scheduled Scanning

Recommended: Run security scans weekly even without code changes:

```yaml
name: Security
on:
  schedule:
    - cron: '0 0 * * 1'  # Every Monday at midnight
  workflow_dispatch:      # Allow manual trigger

jobs:
  security:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-security.yml@main
```

## Tips

1. Pin to version: Use `@v1.0.0` instead of `@main` for production
2. Scheduled scans: Run weekly to catch new vulnerabilities
3. SARIF upload: Keep enabled to track issues in GitHub Security tab
4. Selective scanning: Disable scanners you don't need to reduce run time
5. Custom severity: Adjust Trivy severity based on your risk tolerance

## Related Workflows

- [Go CI](./go-ci-workflow.md) - Continuous integration testing
- [Go Release](./go-release-workflow.md) - Automated release creation

---

**Last Updated:** 2025-11-22
**Version:** 1.0.0
