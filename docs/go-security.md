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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-security.yml@tier-1
```

### Custom Configuration

```yaml
name: Security
on: [push, pull_request]

jobs:
  security:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-security.yml@tier-1
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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-security.yml@tier-1
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
| `govulncheck_version` | govulncheck version to install. Pinned rather than `@latest` so an upstream release cannot change what runs here unchosen. Works at any `go_version` — the install step overrides `GOTOOLCHAIN=auto`, the scan still runs under the pinned toolchain | No | `v1.7.0` |
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

Two things keep this step alive across Go releases:

- **`govulncheck_version`** (default `v1.7.0`) pins the tool, so an upstream release cannot change
  what runs here without someone choosing it. `golang.org/x/vuln` v1.8.0 raised its own `go`
  directive to 1.26.0 and broke every Go repo on this channel the day it shipped; unlike
  `Run govulncheck`, the install step has no `continue-on-error`, so that refusal fails the job.
- **`GOTOOLCHAIN=auto` on the install step only.** `actions/setup-go` exports `GOTOOLCHAIN=local`
  for the whole job, which makes `go install` refuse any tool whose `go` directive is newer than
  `go_version` rather than upgrading — v1.7.0 declares `go 1.25.0` and would not install under the
  default `go_version: 1.23`. The override is scoped to building the scanner; `govulncheck ./...`
  still analyses your module under the pinned toolchain, which is the part that must not drift.

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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-security.yml@tier-1
```

### Critical Scanners Only

```yaml
jobs:
  security:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-security.yml@tier-1
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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-security.yml@tier-1
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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-security.yml@tier-1
```

## Tips

1. Pin to version: Use `@v1.0.0` instead of `@v1.0.0` for production
2. Scheduled scans: Run weekly to catch new vulnerabilities
3. SARIF upload: Keep enabled to track issues in GitHub Security tab
4. Selective scanning: Disable scanners you don't need to reduce run time
5. Custom severity: Adjust Trivy severity based on your risk tolerance

## Related Workflows

- [Go CI](./go-ci.md) - Continuous integration testing
- [Go Release](./go-release.md) - Service release umbrella (semantic-release + Docker + GitOps)

---

**Last Updated:** 2025-11-22
**Version:** 1.0.0
