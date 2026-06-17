# Github-actions-shared-workflows Changelog

## [1.34.0](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.34.0)

- **Features:**
  - Default `enable_ghcr` to true in `go-release` and `build`.
  - Add `dry_run` input and preflight-validate backmerge config in release workflows.
  - Orchestrate backmerge via `backmerge-sync` instead of semantic-release plugin.
  - Enforce coverage threshold by default in `go-pr-analysis`.
  - Expose `golangci_lint_args` and `app_name_prefix` in `go-pr-validation`.

- **Fixes:**
  - Drop trailing blank line in `.releaserc.yml` to satisfy `yamllint`.
  - Split `golangci_lint_args` via `read -ra` to satisfy `shellcheck`.
  - Map `golangci_lint_args` via env to prevent shell injection.

Contributors: @bedatty, @lerian-studio,

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.33.1...v1.34.0)

---

## [1.33.1](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.33.1)

- Fixes:
  - Include `ready_for_review` in change gate condition for Go PR validation.
  - Add Go PR validation and service release umbrella workflows.
  - Post PR comment even when `lerian-lib-version` check fails.
  - Log non-200 HTTP code from releases API in `lerian-lib-version`.
  - Use `MANAGE_TOKEN` for PR comment in nested reusable context in `lerian-lib-version`.

Contributors: @bedatty, @ferr3ira-gabriel, @lerian-studio.

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.33.0...v1.33.1)

---

## [1.33.0](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.33.0)

- **Features**
  - Register forge under `app_helmfile_env` (cross).
  - Keep highest stable semver as GitHub Latest on release (closes `#389`).

- **Fixes**
  - Fail closed on unparsable major and make PR listing non-fatal.
  - Quote inner expansion in parameter strip (`SC2295`).
  - Close superseded update PRs for the same chart and major line.

- **Improvements**
  - Guard git tag pipelines against `SIGPIPE` in `gptchangelog` (closes `#388`).
  - Bump `goreleaser/goreleaser-action` in the `go-tooling` group.

Contributors: @bedatty, @dy-shimizu, @fredcamaral.

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.32.0...v1.33.0)

---

## [1.31.0](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.31.0)

- **Features:**
  - Register `severino-bot` for benedita in the deployment matrix.
  - Register `lerian-hq` in the deployment matrix for benedita.

- **Improvements:**
  - Bump `actions/create-github-app-token` in the release group.

Contributors: @bedatty, @ferr3ira-gabriel, @lerian-studio, @prymax10.

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.30.0...v1.31.0)

---

## [1.30.0](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.30.0)

- **Features**
  - Register `plugin-br-pix-switch` for firmino in the deployment matrix.

- **Fixes**
  - Update self-pr-validation to re-run on PR edited and ready_for_review events.

- **Improvements**
  - Bump `trufflesecurity/trufflehog` dependency.
  - Register `lerian-notification` on firmino in the deployment matrix.

Contributors: @bedatty, @ferr3ira-gabriel, @lerian-studio.

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.29.0...v1.30.0)

---

## [1.29.0](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.29.0)

- **Features:**
  - Add reusable Helm upgrade documentation workflow.

- **Fixes:**
  - Update Helm upgrade documentation for runner type and permissions.
  - Resolve shellcheck violations in helm-release-notification workflow.
  - Add Slack notification inputs for PR review in Helm upgrade documentation workflow.
  - Increase `max_tokens` for API requests in documentation generation script.
  - Enhance Helm upgrade command for specific chart names and improve documentation generation context.

Contributors: @bedatty, @guimoreirar, @lerian-studio.

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.28.13...v1.29.0)

---

## [1.28.13](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.28.13)

- Fixes:
  - Allowlist `gitops_repository` for privileged checkout in `gitops-update`.
  - Honor SARIF `result.suppressions` in `pr-security-reporter`.
  - Dedupe source-branch feedback and add summary comment in `pr-validation`.
  - Make ArgoCD sync resilient with prune/async/timeout in `gitops-update`.
  - Validate `github-script` output before parsing in `security-reporter`.

Contributors: @bedatty, @lerian-studio

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.28.12...v1.28.13)

---

## [1.28.12](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.28.12)

- Fixes:
  - Keep chatty git/gh output off the JSON result stream to prevent leaks in propagation.

- Contributors: @bedatty, @lerian-studio,

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.28.11...v1.28.12)

---

## [1.28.11](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.28.11)

- Fixes:
  - Drop unmatched `::endgroup::` in empty-globs guard to prevent errors.
  - Pass `workflow_files` as a bash array to `apply-bump` for better handling of file lists.

- Improvements:
  - Refuse empty `workflow_files` for a target to ensure proper configuration.

Contributors: @bedatty, @lerian-studio

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.28.10...v1.28.11)

---

## [1.28.10](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.28.10)

- Fixes:
  - Chain version propagation into self-release on `main`.

Contributors: @bedatty, @lerian-studio.

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.28.9...v1.28.10)

---

## [1.28.9](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.28.9)

- Fixes:
  - Always wrap version references in backticks to ensure consistency in `gptchangelog`.

Contributors: @bedatty, @lerian-studio

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.28.8...v1.28.9)

---

## [1.28.8](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.28.8)

- **Fixes**
  - Corrected empty-PR detection and broadened glob matching for backmerge.
  - Skipped non-existent labels instead of failing PR creation in backmerge-sync.
  - Added composite for branch sync with direct/PR/fallback modes in backmerge-sync.

- **Improvements**
  - Pinned composite to @v1 and workflow examples to @v1.28.8 for backmerge.
  - Added persist-credentials to matrix fan-out example in backmerge-sync documentation.

Contributors: @bedatty, @lerian-studio

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.28.7...v1.28.8)

---

## [1.28.7](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.28.7)

- Fixes:
  - Anchor coverage grep to summary line only in go-pr-analysis.

Contributors: @fredcamaral, @lerian-studio,

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.28.6...v1.28.7)

---

## [1.28.6](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.28.6)

- **Fixes**
  - Expose cosign retry tuning and continue GitOps process on signing failure.
  - Forward `ignore_file` to Trivy Image Scan for improved security scan handling.
  - Correct Kustomize download URL in GitOps update process.

- **Improvements**
  - Pin `aquasecurity/trivy-action` to version `v0.35.0` for stability.

Contributors: @bedatty, @lerian-studio

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.28.5...v1.28.6)

---

## [1.28.5](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.28.5)

- Fixes:
  - Expose `protected_branches` input and pin sub-refs to `@v1`.

Contributors: @bedatty, @lerian-studio

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.28.4...v1.28.5)

---

## [1.28.4](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.28.4)

- Fixes:
  - Added reusable repository-routine workflow.

Contributors: @bedatty, @lerian-studio

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.28.3...v1.28.4)

---

## [1.28.3](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.28.3)

- Fixes:
  - Register ungoliant-controller on anacleto.
  - Add merge-readiness verdict and per-stage summary to pr-security-reporter.
  - Add kustomize layout support to gitops-update.

Contributors: @bedatty, @lerian-studio,

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.28.2...v1.28.3)

---

## [1.28.2](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.28.2)

- Fixes:
  - Direct push to default branch and auto-backmerge in `gptchangelog`.

Contributors: @bedatty, @lerian-studio

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.28.1...v1.28.2)

---

## [1.28.1](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.28.1)

Features:
- Extracted `gptchangelog` into a reusable composite for improved workflow management.

Improvements:
- Updated CHANGELOGs for `github-actions-shared-workflows` to version v1.28.0.

Fixes:
- Bumped `securego/gosec` in the security-scanners group to enhance security measures.

Contributors: @bedatty, @lerian-studio

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.28.0...v1.28.1)

---

## [1.28.0](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.28.0)

- **Features:**
  - Register `plugin-bc-correios` in the deployment matrix.

- **Fixes:**
  - Handle filenames with spaces in directory names and validate `system_packages` tokens in `changed-paths` and `go-pr-analysis`.
  - Use `mapfile` to parse `system_packages` handling spaces and newlines in `go-pr-analysis`.
  - Use `read -ra array` to avoid SC2086 in `system_packages` install for `go-pr-analysis`.
  - Expose `ignorefile` input for path-scoped suppression in `trivy-fs-scan`.

- **Improvements:**
  - Pin `actions/checkout` by SHA and standardize internal composite refs to `@v1` in `changed-paths`.
  - Reduce workflow runs retention to 45 days and tighten stale thresholds.

Contributors: @bedatty, @lerian-studio, @prymax10

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.27.5...v1.28.0)

---

## [1.27.5](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.27.5)

- **Features:**
  - Collapse self-routine to a single weekly cron firing all jobs.

- **Fixes:**
  - Correct upload-artifact v7 SHA in go-security.
  - Pin remaining external actions by SHA in go-security.
  - Add missing github-actions label for Dependabot.
  - Collapse actions/stale verbose log and add custom summary.

- **Improvements:**
  - Skip release when only self-* workflows change.

Contributors: @bedatty, @lerian-studio

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.27.4...v1.27.5)

---

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

