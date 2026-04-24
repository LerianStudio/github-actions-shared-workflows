# Github-actions-shared-workflows Changelog

## [1.26.4](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.26.4)

- Fixes:
  - Unified entrypoint for repository maintenance routines.
  - Robust HTTP status parsing from GitHub API output.
  - Tracking protection-check failures in a dedicated counter.
  - Hardened protection check and addressed code-injection findings.
  - Avoided SIGPIPE when checking branch protection.

Contributors: @bedatty, @lerian-studio

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.26.3...v1.26.4)

---

## [1.26.3](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.26.3)

- Fixes:
  - Removed major version tag alias to improve build consistency.
  - Supported golangci-lint v2 module path in the CI installer.
  
- Improvements:
  - Simplified backmerge PR title for clarity.
  - Added benedita cluster to the deployment matrix.

Contributors: @bedatty, @lerian-studio

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.26.2...v1.26.3)

---

## [1.26.2](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.26.2)

- **Fixes:**
  - Skip Slack notification in sync PR when webhook is unset.
  - Add backmerge PR fallback for divergent develop branch in TypeScript release.
  - Mitigate code injection by mapping inputs to environment variables.
  - Add retry with exponential backoff for transient OIDC failures in cosign-sign.

- **Improvements:**
  - Pin changed-paths composite to floating major tag for gptchangelog and TypeScript release.
  - Harden installer and quote refs per CodeRabbit review.
  - Pin external actions by SHA and fix shellcheck issues in go-pr-analysis.

Contributors: @bedatty, @lerian-studio

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.26.1...v1.26.2)

---

## [1.26.1](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.26.1)

- Fixes:
  - Addressed CodeQL medium findings to improve security.
  - Renamed deprecated app-id input to client-id to align with updated standards.
  - Filtered dismissed and fixed alerts from PR comments in the CodeQL reporter.
  - Enforced composite vs reusable pinning policy for pinned actions.

Contributors: @bedatty, @lerian-studio

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.26.0...v1.26.1)

---

## [1.26.0](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.26.0)

- **Features:**
  - Generate changelog automatically after a stable release on the main branch.

- **Fixes:**
  - Resolve contributors using the GitHub API instead of relying on the email local-part.

- **Improvements:**
  - Document the `deployment_matrix_ref` input and its resolution to the main-default.

Contributors: @bedatty,

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.25.0...v1.26.0)

