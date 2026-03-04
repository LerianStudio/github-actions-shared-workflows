<p align="center">
  <img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" />
  <br/>
  <strong>Lerian — Security Policy</strong>
</p>

# Security Policy

## Scope

This policy applies to the **GitHub Actions Shared Workflows** repository (`LerianStudio/github-actions-shared-workflows`), which provides reusable CI/CD workflows used across the entire Lerian organization.

Because a vulnerability here can affect **every repository** that references these workflows, we treat security issues in this repo with the highest priority.

## Supported Versions

We actively maintain and patch the following refs:

| Ref | Status |
|---|---|
| `@main` | Supported — production releases |
| `@develop` | Supported — pre-release (beta) |
| `@vX.Y.Z` (latest minor) | Supported |
| `@vX.Y.Z` (older tags) | Not actively patched — upgrade to latest |

We strongly recommend always pinning callers to the latest stable tag rather than `@main` for production workloads.

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Report security issues privately through one of the following channels:

- **GitHub Private Vulnerability Reporting** (preferred):
  Navigate to [Security → Report a vulnerability](https://github.com/LerianStudio/github-actions-shared-workflows/security/advisories/new) in this repository.

- **Email** (alternative): Send a report to [security@lerian.studio](mailto:security@lerian.studio). Include `[SECURITY] github-actions-shared-workflows` in the subject line.

### What to include in your report

Please provide as much of the following as possible:

- A clear description of the vulnerability and its potential impact
- The affected workflow file(s) and the specific step or input involved
- Steps to reproduce or a proof-of-concept (if safe to share)
- The version/ref where the issue was observed
- Any suggested mitigations or fixes

## Response Timeline

| Stage | Target |
|---|---|
| Initial acknowledgment | Within 2 business days |
| Severity assessment | Within 5 business days |
| Fix or mitigation published | Based on severity (see below) |
| Public disclosure | After fix is available and callers have been notified |

### Severity-based fix timeline

| Severity | Target fix time |
|---|---|
| Critical (CVSS ≥ 9.0) | 48 hours |
| High (CVSS 7.0–8.9) | 7 days |
| Medium (CVSS 4.0–6.9) | 30 days |
| Low (CVSS < 4.0) | Next release cycle |

## Security Measures in This Repository

This repository applies the following controls to protect callers:

- **Dependabot** monitors all third-party GitHub Actions and opens PRs weekly with version updates.
- **`pr-security-scan.yml`** runs Trivy and secret scanning on every PR.
- **`go-security.yml`** provides Gosec, govulncheck, Nancy, TruffleHog, license checks, and SBOM generation for Go projects.
- **CODEOWNERS** ensures all changes to security-sensitive workflows require explicit review from `@LerianStudio/devops-team`.
- **Semantic versioning** with GPG-signed tags ensures callers can pin to verified, immutable refs.
- **Branch protection** on `main` and `develop` prevents direct pushes.

## Supply Chain Security Recommendations for Callers

When consuming workflows from this repository:

1. **Pin to a specific tag** (`@v1.2.3`) rather than `@main` in production.
2. **Review Dependabot PRs** raised in this repo before your workflows pick up updated refs.
3. **Subscribe to releases** on this repository to be notified of security patches.
4. **Never pass secrets as plain inputs** — always use `secrets:` blocks when calling reusable workflows.

## Disclosure Policy

We follow a **coordinated disclosure** model:

1. Vulnerability is reported privately.
2. We assess severity and develop a fix.
3. A patched release is published and affected teams are notified.
4. A public GitHub Security Advisory is published after callers have had time to update.

We credit reporters in the advisory unless anonymity is requested.

## Contact

For non-security questions about these workflows, open a [GitHub Discussion](https://github.com/LerianStudio/github-actions-shared-workflows/discussions) or mention `@LerianStudio/devops-team` in an issue or PR.
