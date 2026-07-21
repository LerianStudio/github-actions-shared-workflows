# Github-actions-shared-workflows Changelog

## [1.47.0](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.47.0)

Features:
- Standardize runners via `vars.RUNNER_LABEL` across shared workflows. (@gandalf-at-lerian)

Fixes:
- Merge changes from develop to main. (@bedatty)
- Standardize runner variables by renaming to `vars.GENERAL_RUNNERS` and ensure fallback to `ubuntu-latest` instead of blacksmith. (@bedatty)
- Avoid shell injection in dry-run runner echo. (@bedatty)
- Restore blacksmith fallback while keeping network runners authoritative. (@bedatty)
- Default `enable_dockerhub` to true for JS/TS builds. (@bedatty)
- Register lender (benedita + anacleto) in the deployment matrix. (@prymax10)
- Register br-sisbajud (benedita + anacleto) in the deployment matrix. (@bedatty)
- Add jitter and delay cap to cosign retry backoff and address CodeRabbit findings on the same. (@bedatty)

Improvements:
- Bump `Mattraks/delete-workflow-runs` to `v2.1`. (@bedatty)

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.46.5...v1.47.0)

---

## [1.46.5](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.46.5)

Fixes:

- Resolved an issue with the release process by merging changes from `develop` to `main`. (@bedatty)
- Limited the retry wall-clock time for `aws-cli` and configured `dirmngr.conf` for keyserver timeout. (@bedatty)
- Bounded the network fetches during the `aws-cli` installer process. (@bedatty)
- Addressed findings from CodeRabbit on release PR `#590`. (@bedatty)
- Added an end-to-end tests job with Allure/S3 report for Palantir in the `go-release` workflow. (@bedatty)
- Skipped the `release-diff` trigger for CI/meta-only changes in the `ungoliant` workflow. (@bedatty)
- Introduced a major-bump grace window in the `lib-version-check` workflow. (@bedatty)

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.46.4...v1.46.5)

---

## [1.46.4](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.46.4)

Fixes:
- Merged changes from `develop` to `main` to address release issues. (@bedatty)
- Added explicit `!cancelled()` condition to the `s3_upload` gate in the go-release workflow to prevent premature cancellations. (@bedatty)
- Removed reliance on unreliable build results for gating `s3_upload` in the go-release workflow. (@bedatty)

Improvements:
- Included `br-slc` in the deployment matrix to enhance deployment coverage. (@bedatty, @gandalf-at-lerian)

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.46.3...v1.46.4)

---

## [1.46.3](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.46.3)

Fixes:
- Merged changes from `develop` to `main` to ensure the latest updates are reflected in the primary branch. (@bedatty)
- Addressed findings from CodeRabbit on the pull request merging `develop` to `main`. (@bedatty)
- Added `tag_prefix` for `extra_builds` and frontend quality gates to improve the release process. (@bedatty)

Improvements:
- Updated documentation to include `shared_paths/normalize_to_filter` in the monorepo scope note, ensuring clarity on its inclusion. (@bedatty)

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.46.2...v1.46.3)

---

## [1.46.2](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.46.2)

Features:
- Added npm publish support and configured JavaScript project validation paths for monorepos. (@bedatty)

Fixes:
- Corrected the release process to ensure the transition from `develop` to `main`. (@bedatty)
- Forwarded `dockerfile_name` and `extra_builds` parameters for stable releases in the Go release workflow. (@fredcamaral)
- Enabled fetching of git notes to allow `semantic-release` to promote prereleases to stable versions. (@bedatty)
- Implemented sorting of tags using `versionsort.suffix` to prioritize stable releases over prereleases. (@bedatty)
- Made the ArgoCD application wait timeout configurable with retry backoff in the GitOps update process. (@bedatty)
- Increased the default `curl-timeout` from 300 seconds to 900 seconds in the Ungoliant workflow. (@bedatty)

Improvements:
- Renamed the matrix entry from `gestao-acessos-console` to `severino`. (@prymax10)
- Clarified the wording regarding retry attempts in the GitOps update documentation. (@bedatty)
- Documented the `curl-timeout` lockstep requirement in the Ungoliant README. (@bedatty)

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.46.1...v1.46.2)

---

## [1.46.1](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.46.1)

Fixes:
- Removed the vars expression from the input description in the prerelease-check workflow. (@bedatty)

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.46.0...v1.46.1)

---

## [1.46.0](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.46.0)

Features:
- Allow overriding the prerelease-check pattern via an organization variable. (@bedatty)

Fixes:
- Improve the robustness of the previous-tag fallback, add retries, and implement a fail-fast health check in the ungoliant-release-diff workflow. (@bedatty)
- Add a reusable workflow and composite for the controller release-diff in the ungoliant-release-diff workflow. (@bedatty)
- Use a keyword allowlist in the prerelease-check to avoid false positives due to vendor-suffixes. (@bedatty)
- Validate pattern overrides and treat underscores as tokens in the prerelease-check. (@bedatty)
- Require a token boundary after the pre-release keyword in the prerelease-check. (@bedatty)
- Reword a comment in the prerelease-check to satisfy the spell check. (@bedatty)
- Fix the release process from `develop` to `main`. (@bedatty)

Improvements:
- Bump `trufflesecurity/trufflehog` from `3.95.6` to `3.95.8` in the security-scanners group. (@bedatty)
- Update the github-security group with two dependency updates. (@bedatty)

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.45.0...v1.46.0)

---

## [1.45.0](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.45.0)

Features:
- Add Go Lambda release workflow. (@guimoreirar)
- Add Go Lambda release workflow and build action. (@guimoreirar)
- Add Go Lambda release workflow and build action with documentation. (@guimoreirar)

Fixes:
- Adjust permissions for AWS OIDC and update build action reference to use `develop` branch. (@guimoreirar)
- Update build action reference for Go Lambda artifact to pin to `main` for stable releases. (@guimoreirar)
- Update build action reference for Go Lambda artifact to use the feature branch. (@guimoreirar)

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.44.1...v1.45.0)

---

## [1.44.1](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.44.1)

Fixes:

- Ensure the release process correctly transitions from `develop` to `main`. (@bedatty)
- Make environment targets configurable for `stable`, `rc`, and `beta` releases in the GitOps update process. (@bedatty)
- Use a channel-aware S3 path for uploading E2E reports in the JavaScript release workflow. (@bedatty)
- Register `br-sta` in the Benedita deployment matrix. (@bedatty)
- Register the underwriter in the Benedita deployment matrix. (@bedatty)

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.44.0...v1.44.1)

---

## [1.44.0](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.44.0)

Features:
- Promote prerelease `allow-file` to main, enhancing security checks for pre-release versions. (@fredcamaral)
- Allowlist accepted pre-release pins in the prerelease-check to improve flexibility in version management. (@fredcamaral)

Fixes:
- Normalize the `go.mod` require keyword in `allow-file` matching to ensure consistent dependency management. (@fredcamaral)

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.43.1...v1.44.0)

---

## [1.43.1](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.43.1)

Fixes:

- Corrected the release process to ensure changes from `develop` are properly merged into `main`. (@bedatty)
- Improved the `go-release` workflow by cleanly skipping the `update_gitops` step when only `extra_build` has run. (@bedatty)

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.43.0...v1.43.1)

---

## [1.43.0](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.43.0)

Features:
- Added the `prerelease_backmerge_sync_enabled` input, which is opt-in and defaults to false. (@bedatty)
- Registered `mock-btg-server` for the benedita gitops-update in the deployment matrix. (@bedatty)

Fixes:
- Corrected the release process from `develop` to `main`. (@bedatty)

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.42.0...v1.43.0)

---

## [1.42.0](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.42.0)

Features:
- Added an optional end-to-end test job after the build on tag push for JavaScript releases. (@bedatty)
- Implemented the upload of Playwright reports to S3 in the `e2e_tests` job for JavaScript releases. (@bedatty)
- Introduced the `build_on_release` feature to publish GA images during the run, available as an opt-in for Go releases. (@fredcamaral)

Fixes:
- Resolved an issue where the release process incorrectly picked the published version/tag by glob order instead of by timestamp. (@bedatty)
- Updated the release process to use nanosecond-resolution timestamps to avoid tie-breaks. (@bedatty)
- Fixed a shellcheck SC2129 issue in the publish status aggregation script. (@bedatty)
- Addressed CodeQL findings related to the release process. (@bedatty)
- Reverted the `prerelease-guard` reference back to `@v1`. (@bedatty)
- Addressed CodeRabbit findings on the release process. (@bedatty)
- Resolved CodeRabbit security findings for JavaScript releases. (@bedatty)
- Enhanced the backmerge-sync process to retry fetch operations to handle post-push ref-advertisement lag. (@fredcamaral)

Improvements:
- Added an optional end-to-end test job after the build on tag push for JavaScript releases. (@bedatty)

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.41.0...v1.42.0)

---

## [1.41.0](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.41.0)

Features:
- Add reusable workflows for Helm alpha release and cleanup. (@guimoreirar)

Fixes:
- Correct the release process by merging `develop` into `main`. (@bedatty)
- Prevent reliance on unevaluated expressions as input defaults in the prerelease guard. (@bedatty)
- Address issues in the release process by pointing the prerelease-guard ref at `develop` until `v1` catches up. (@bedatty)
- Guard `release.yml` against prerelease versions published after stable releases. (@bedatty)
- Address code review feedback on prerelease gates. (@bedatty)
- Prevent script injection by passing references via environment variables in the Helm alpha release workflow. (@guimoreirar)

Improvements:
- Bump `trufflesecurity/trufflehog` from `3.95.5` to `3.95.6` in the security-scanners group. (@bedatty)
- Update the GitHub security group with two dependency updates. (@bedatty)
- Refactor Helm alpha workflows for improved clarity and functionality. (@guimoreirar)
- Update the container retention policy to use a pinned SHA `v3.1.0`. (@guimoreirar)

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.40.4...v1.41.0)

---

## [1.40.4](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.40.4)

Fixes:
- Corrected the release process by merging `develop` into `main`. (@bedatty)
- Sanitized `filter_paths` injection by mapping environment variables to prevent security issues identified by CodeQL. (@bedatty)
- Addressed feedback from CodeRabbit review on PR `#523`. (@bedatty)
- Improved changelog generation by filtering out bot and irrelevant commits. (@bedatty)

Features:
- Introduced `js-pr-validation.yml`, an umbrella workflow for JavaScript/TypeScript repositories to streamline pull request validation. (@bedatty)
- Added `js-release.yml`, an umbrella workflow for JavaScript/TypeScript repositories to facilitate the release process. (@bedatty)

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.40.3...v1.40.4)

---

## [1.40.3](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.40.3)

Fixes:
- Ensure `generate_changelog` runs after `update_major_tag` to resolve `gptchangelog@v1` to the current code. (@bedatty)
- Allow `generate_changelog` execution when `update_major_tag` is skipped. (@bedatty)
- Remove type prefix repetition in bullets and group them under plain section headers. (@bedatty)

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.40.2...v1.40.3)

---

## [1.40.2](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.40.2)

- Fix: Corrected the release process from `develop` to `main` to ensure proper workflow transitions (@bedatty).
- Fix: Improved the `gptchangelog` by attributing contributors inline per bullet point instead of using a trailing list, enhancing clarity and readability (@bedatty).
- Fix: Optimized `gptchangelog` by folding commit subjects into the git log pass, reducing the need for extra subprocesses (@bedatty).
- Fix: Adjusted the `gptchangelog` to delete `api_response.json` after reading with `jq`, preventing premature deletions and potential errors (@bedatty).

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.40.1...v1.40.2)

---

## [1.39.0](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.39.0)

- **Features:**
  - Add `force_full_matrix` opt-in input for tightly-coupled components.

- **Fixes:**
  - Ensure `normalize_to_filter` is a boolean, not a string, in `extra_build`.
  - Prevent code injection via `coverage_threshold` interpolation in `go-pr-analysis`.
  - Rename `lerian-notification` to `notifications` in deployment matrix.
  - Always build all components on tag push.

Contributors: @bedatty, @lerian-studio.

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.38.0...v1.39.0)

---

## [1.38.0](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.38.0)

- **Features:**
  - Expose monorepo security parameters to security scan in `go-pr-validation`.
  - Develop branch merged into main for release.

- **Fixes:**
  - Guard `extra_build` against empty JSON array in `go-release`.

Contributors: @bedatty, @lerian-studio.

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.37.0...v1.38.0)

---

## [1.37.0](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.37.0)

- **Features:**
  - Added support for per-cluster environment suffix variants (`-st` / `-mt`).
  - Renamed `ARGOCD_GHUSER_TOKEN` to `ARGOCD_TOKEN`.
  - Resolved `ARGOCD_URL` from organization variable instead of secret.
  - Removed `runner_type` input; runner resolved exclusively from `GITOPS_RUNNERS` organization variable.
  - Added `update_sandbox` boolean and resolved `gitops_repository` from organization variable.

- **Fixes:**
  - Added `lerian-map` as a cross app in deployment matrix for `benedita`.
  - Restored `ungoliant-controller` and `severino-bot` for kustomize cluster resolution.
  - Avoided code injection by passing `yq_version` via environment instead of run interpolation.
  - Fixed `env_contexts` early return, `argocd` rc capture, and runner fallback.
  - Installed `yq` and `argocd` without `sudo` using `~/.local/bin`.

- **Improvements:**
  - Skipped `argocd` and `yq` downloads when already installed on runner.
  - Removed `firmino` and `clotilde` clusters; synced matrix with internal audit.
  - Aligned deployment matrix with internal audit.
  - Resolved runner from `GITOPS_RUNNERS` organization-level variable.
  - Set `update_sandbox` default to `false`.

Contributors: @bedatty, @ferr3ira-gabriel, @gandalf-at-lerian, @lerian-studio.

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.36.8...v1.37.0)

---

## [1.36.8](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.36.8)

- Fixes:
  - Support both legacy and package-directory layouts for README updates in `helm-update` (#489, #488, 247b058)

- Improvements:
  - Update CHANGELOGs for `github-actions-shared-workflows`:`v1.36.7` [skip ci]

Contributors: @guimoreirar, @lerian-studio.

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.36.7...v1.36.8)

---

## [1.36.7](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.36.7)

- Fixes:
  - Forward `normalize_to_filter` in `extra_builds` entries.
  - Fail on invalid `s3_uploads` JSON and sync `runner_type` docs.
  - Enforce `s3_uploads` is a JSON array.
  - Support per-entry `aws_role_arn` in `s3_uploads`.
  - Default to `eveo-lxc-runners` instead of `firmino-lxc-runners`.

Contributors: @bedatty, @ferr3ira-gabriel, @lerian-studio.

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.36.6...v1.36.7)

---

## [1.36.6](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.36.6)

- Fixes:
  - Fixed the release process by merging `develop` into `main` (#477).
  - Modified `go-release` to run `s3_upload` inline instead of using a matrix over a reusable workflow (#476).
  - Hardened `s3_upload` checkout and tightened the production tag regex in `go-release`.

- Improvements:
  - Updated CHANGELOGs for `github-actions-shared-workflows`:`v1.36.5` [skip ci].

Contributors: @bedatty, @lerian-studio.

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.36.5...v1.36.6)

---

## [1.36.5](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.36.5)

- Fixes:
  - Forward `filter_paths` and `path_level` to security scan in `go-pr-validation`.
  - Correct release process from `develop` to `main`.

Contributors: @bedatty, @lerian-studio

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.36.4...v1.36.5)

---

## [1.36.4](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.36.4)

- Fixes:
  - Fix release process by merging `develop` into `main` (#468).
  - Expose and forward `filter_paths` and `path_level` in `go-pr-validation` (#467).
  - Type `path_level` as a number to match `go-pr-analysis`.

Contributors: @bedatty, @lerian-studio

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.36.3...v1.36.4)

---

## [1.36.3](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.36.3)

- Fixes:
  - Fix release process by merging `develop` into `main` (#464).
  - Add `dockerfile_path` to scan component Dockerfiles in PR security scan (#463).

Contributors: @bedatty, @lerian-studio.

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.36.2...v1.36.3)

---

## [1.36.2](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.36.2)

- Fixes:
  - Fix: Expose and forward `enable_docker_scan` in `go-pr-validation`.
  - Fix: Develop to main release process.

Contributors: @bedatty, @lerian-studio.

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.36.1...v1.36.2)

---

## [1.36.1](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.36.1)

- Fixes:
  - Forward `strip_prefix` and `flatten` in `s3_uploads` entries for `go-release`.
  - Correct release process from `develop` to `main`.

Contributors: @bedatty, @lerian-studio

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.36.0...v1.36.1)

---

## [1.36.0](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.36.0)

- **Features:**
  - Added opt-in S3 upload job after build for migration files in `go-release`.
  - Added opt-in ApiDog E2E test job after gitops-update in `go-release`.
  - Derived gitops `app_name`, commit prefix, and artifact pattern from `app_name_prefix` in `go-release`.
  - Supported multiple build groups via `extra_builds` in `go-release`.

- **Fixes:**
  - Ensured `lerian-lib-version` honors `ignore-pin` before the releases API call.
  - Made `go-pr-validation` fail gates when the changes job errors.
  - Implemented pre-flight tag existence check and restored `continue-on-signing-failure` in build.
  - Shipped default `.ignorecoverunit` coverage exclusions in `go-pr-analysis`.
  - Made prerelease-check annotation branch-aware in security.

Contributors: @bedatty, @lerian-studio.

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.35.1...v1.36.0)

---

## [1.35.1](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.35.1)

- Fixes:
  - Add `release_single_app` for single-release multi-build monorepos in `go-release`.
  - Hand changed-file list off via temp file to avoid `ARG_MAX` overflow in `changed-paths`.

Contributors: @bedatty, @fredcamaral, @lerian-studio

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.35.0...v1.35.1)

---

## [1.35.0](https://github.com/LerianStudio/github-actions-shared-workflows/releases/tag/v1.35.0)

- **Features**
  - Expose `helm-dispatch` and `gitops-update` inputs for multi-cluster deploy in `go-release`.

- **Fixes**
  - Exclude pre-release tags when resolving the latest version in `lerian-lib-version`.

- **Improvements**
  - Clarify `deploy_in_*` as force-off overrides, not additive selectors in documentation for `go-release`.

Contributors: @bedatty, @lerian-studio.

[Compare changes](https://github.com/LerianStudio/github-actions-shared-workflows/compare/v1.34.0...v1.35.0)

---

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

