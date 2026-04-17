# Github-actions-shared-workflows Changelog

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

