# Github-actions-shared-workflows Changelog

## [1.27.4](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.27.4)

- Fixes:
  - Fix(stale): Pre-flight scope banner before actions/stale per-item log.
  - Fix(branch-cleanup): Abort on protected-branch prefetch failure.
  - Fix(branch-cleanup): Use /branches?protected=true to detect rule-protected branches.

Contributors: @bedatty, @lerian-studio,

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.27.3...v1.27.4)

---

## [1.27.3](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.27.3)

- Fixes:
  - Unpinned branch-cleanup and labels-sync composites to @v1.

Contributors: @bedatty, @lerian-studio

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.27.2...v1.27.3)

---

## [1.27.2](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.27.2)

- Fixes:
  - Pin `actions/checkout` by SHA in labels-sync to ensure consistency.
  - Rename input in labels-sync composite and update the default pattern for workflow-runs-cleanup.

- Improvements:
  - Clarify the semantics of literal substring match in workflow-runs-cleanup documentation.

Contributors: @bedatty, @lerian-studio

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.27.1...v1.27.2)

---

## [1.27.1](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.27.1)

- Fixes:
  - Tightened triggers for self-routine workflows to improve efficiency.

Contributors: @bedatty, @lerian-studio

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.27.0...v1.27.1)

---

## [1.27.0](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.27.0)

Features:
- Refactor stale logic by splitting stale PR and issue logic into separate workflows.

Fixes:
- Use external references for reusable workflow composition in stale workflow.

Contributors: @bedatty, @lerian-studio,

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.26.4...v1.27.0)

---

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

