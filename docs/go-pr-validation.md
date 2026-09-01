<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>go-pr-validation</h1></td>
  </tr>
</table>

Umbrella reusable workflow for Go service repositories. A caller references this single workflow and it orchestrates everything a Go service PR needs:

1. **PR metadata** — title, source branch, size, labels (delegates to `pr-validation.yml`).
2. **Breaking Change Guard** — mandatory detection and enforcement inherited from `pr-validation.yml` for every PR target branch.
3. **Change gate** — detects whether the PR touches anything beyond docs/meta (`src/config/non-doc-changes`); documentation-only PRs skip the heavy pipelines.
4. **Go analysis** — lint, tests, coverage and build (delegates to `go-pr-analysis.yml`), opt-in via `run_go_analysis`.
5. **Security scan** — Trivy, CodeQL, prerelease checks (delegates to `pr-security-scan.yml`), opt-in via `run_security`.
6. **Lerian lib version check** — fails when a direct Lerian library is behind its latest stable release (delegates to `lerian-lib-version-check.yml`), opt-in via `run_lib_version_check`.
7. **Permission manifest nudge (RI)** — **non-blocking** reminder that warns via a sticky PR comment when a `lib-auth` repo has no `permissions.yaml` manifest (delegates to `src/validate/permission-manifest-nudge`), opt-in via `run_manifest_nudge`. Never fails and is **not** a required check.

The `go-analysis`, `security` and `lib-version` pipelines each have a `*-gate` aggregator job that exposes a single stable status-check name (`Go Analysis`, `Security`, `Lib Version`) for branch protection, regardless of the internal job names. All three are gated by the change detector, so documentation-only PRs skip them (and the aggregators still report success). If the change detector (`changes`) job itself fails, the aggregators propagate that failure instead of passing — so broken change detection cannot let the required checks go green.

> The aggregators run with `if: always()`, so they report on every run of this workflow. `result-gate` treats `skipped` as a pass, which is correct for the docs-only case (the detector ran and found nothing to analyse) but **not** for a run where the detector never ran at all — that would report the required checks green having evaluated nothing. The `changes` job must therefore stay reachable on every `pull_request` action type the caller listens to, `edited` included. A caller that adds an action type to its own `types:` list without it being covered here reintroduces the hole.

## Inputs

| Input | Description | Type | Default |
|-------|-------------|------|---------|
| `runner_type` | GitHub runner type | string | `blacksmith-4vcpu-ubuntu-2404` |
| `gate_runner_type` | Optional runner override for the umbrella utility jobs only (Detect non-doc changes + Go Analysis / Security / Lib Version result gates); empty falls back to `vars.GENERAL_RUNNERS`, then `runner_type` | string | `''` |
| `lint_runner_type` | Optional runner override for the Go analysis Lint jobs only | string | `''` |
| `test_runner_type` | Optional runner override for the Go analysis Tests jobs only | string | `''` |
| `coverage_runner_type` | Optional runner override for the Go analysis Coverage jobs only | string | `''` |
| `build_runner_type` | Optional runner override for the Go analysis Build jobs only | string | `''` |
| `security_scan_runner_type` | Optional runner override for the security_scan jobs only | string | `''` |
| `pr_checks_summary_runner_type` | Optional runner override for the PR Checks Summary job only | string | `''` |
| `dry_run` | Preview metadata validations without posting comments/labels | boolean | `false` |
| `run_metadata` | Run the PR metadata pipeline (title, scopes, labeler, size, breaking-change guard). Set `false` in a multi-component repository that also calls `js-pr-validation.yml`, so exactly one umbrella owns PR metadata | boolean | `true` |
| `run_go_analysis` | Run the Go analysis pipeline | boolean | `true` |
| `run_security` | Run the security scan pipeline | boolean | `true` |
| `run_lib_version_check` | Run the Lerian library version check | boolean | `true` |
| `run_manifest_nudge` | Run the **non-blocking** Access-Manager RI nudge: warns via a sticky PR comment when a `lib-auth` repo has no `permissions.yaml`. Never fails or blocks the PR. | boolean | `true` |
| `ignore_globs` | Space-separated globs treated as docs/meta for the change gate | string | `*.md docs/* .github/* LICENSE* .gitignore` |
| `lib_version_go_mod_path` | Path to go.mod for the Lerian lib check | string | `go.mod` |
| `lib_version_check_indirect` | Also check transitive (indirect) Lerian deps | boolean | `false` |
| `lib_version_comment_on_pr` | Post/update a sticky PR comment with the lib version table | boolean | `true` |
| `pr_title_types` | Allowed commit types (pipe-separated) | string | conventional set |
| `pr_title_scopes` | Allowed scopes (pipe-separated, empty = any) | string | `''` |
| `require_scope` | Require scope in PR title | boolean | `false` |
| `enable_auto_labeler` | Auto-label by changed files | boolean | `true` |
| `labeler_config_path` | Path to labeler config | string | `.github/labeler.yml` |
| `enforce_source_branches` | Enforce source branches into protected branches | boolean | `true` |
| `allowed_source_branches` | Allowed source branches (pipe-separated, `*` prefix) | string | `develop\|release-candidate\|hotfix/*` |
| `target_branches_for_source_check` | Target branches requiring source validation | string | `main` |
| `require_verified_commits` | Block the PR when any commit is unsigned or unverified | boolean | `true` |
| `go_version` | Go version | string | `1.23` |
| `golangci_lint_version` | GolangCI-Lint version | string | `v1.62.2` |
| `golangci_lint_args` | Extra arguments passed to golangci-lint (e.g. `--timeout=5m`) | string | `--timeout=5m` |
| `app_name_prefix` | Prefix used to namespace coverage/build artifacts | string | `''` |
| `filter_paths` | Newline-separated component path prefixes for monorepo per-component analysis (lint/tests/coverage) **and** security scanning; empty = single-app root run. When using it for security, leave `dockerfile_path` empty so each component Dockerfile is discovered | string | `''` |
| `path_level` | Directory depth level to extract the component name from `filter_paths` | number | `2` |
| `normalize_to_filter` | Collapse every changed file under a `filter_paths` entry into that one component instead of the `path_level`-trimmed directory; forwarded to `go-pr-analysis` | boolean | `true` |
| `coverage_threshold` | Minimum coverage percentage (0-100) | number | `80` |
| `fail_on_coverage_threshold` | Fail when coverage is below threshold | boolean | `true` |
| `go_private_modules` | GOPRIVATE pattern for private modules | string | `''` |
| `enable_integration_tests` | Enable integration tests | boolean | `false` |
| `integration_test_command` | Command for the integration lane. Empty → `make test-integration` | string | `''` |
| `enable_test_determinism` | Enable the test determinism check (repeat runs with shuffle) | boolean | `false` |
| `test_determinism_runs` | Number of repeat runs for the determinism check | number | `3` |
| `enable_custom_checks` | Run arbitrary caller-owned Makefile targets as an extra gate | boolean | `false` |
| `custom_checks` | Newline-separated Makefile targets; each runs via `make <target>`, any non-zero exit fails the job | string | `''` |
| `system_packages` | apt packages to install for CGO repos | string | `''` |
| `ignore_file` | Path to Trivy ignore file | string | `''` |
| `enable_docker_scan` | Build and scan a Docker image with Trivy; set `false` for repos without a root Dockerfile (monorepos with Dockerfiles under `components/`/`cmd/`) | boolean | `true` |
| `dockerfile_path` | Explicit path to a single Dockerfile to build and scan (e.g. `components/ledger/Dockerfile`); lets monorepos without a root Dockerfile keep `enable_docker_scan: true` | string | `''` |
| `build_context_from_working_dir` | Build each component image with its own `working_dir` as the Docker build context instead of the repository root. Required for type1 monorepos whose components are independent modules — a component Dockerfile starting with `COPY go.mod go.sum ./` cannot build from the repository root | boolean | `false` |
| `enable_codeql` | Enable CodeQL static analysis | boolean | `false` |
| `codeql_languages` | CodeQL languages (comma-separated) | string | `''` |
| `monorepo_type` | Monorepo layout for the security scan. `"type1"` = components in separate folders (default). `"type2"` = backend at repo root + one independent component in a sub-folder. | string | `'type1'` |
| `frontend_folder` | Sub-folder treated as an independent scan component in type2 repos (e.g. `"tools/mock-sta-server"`). Ignored when `monorepo_type` is `"type1"`. | string | `'frontend'` |
| `trivy_skip_dirs` | Comma-separated directories to skip in every Trivy filesystem scan (appended to the built-in skip list). Useful for excluding sub-modules from the root scan (e.g. `"tools/mock-sta-server"`). | string | `''` |
| `shared_paths` | Path patterns that trigger analysis/security for all components | string | `''` |
| `enable_coderabbit_gate` | Ask CodeRabbit for a review once this validation passes. Needs only `auto_review.enabled: false` in the repo — see [coderabbit-gate](coderabbit-gate.md) | boolean | `true` |
| `coderabbit_review_base_branches` | Comma-separated exact base branch names whose PRs get a review. Empty removes this dimension | string | `develop` |
| `coderabbit_review_head_patterns` | Comma-separated globs matched against the head branch; a match is reviewed regardless of base | string | `hotfix/*` |
| `coderabbit_gate_label` | Trigger label. Must match `reviews.auto_review.labels` in `.coderabbit.yml` | string | `review-ready` |

The Breaking Change Guard has no dedicated input, enable flag or target-branch filter. This umbrella inherits the guard automatically from `pr-validation.yml`, as part of the metadata pipeline.

> **`run_metadata: false` skips the guard along with the rest of the metadata pipeline.** That input exists so a multi-component repository can run metadata exactly once across several umbrellas — it is not an opt-out from the guard. In such a repository, one umbrella must keep `run_metadata: true`, and that is the one enforcing the guard. Setting it to `false` on every umbrella disables the guard for the repository.
>
> When `run_metadata` is `false`, this workflow's `has_breaking_changes`, `breaking_change_approved` and `breaking_change_result` outputs are still produced, but with no metadata job to supply values they collapse to their fail-closed fallbacks — `false`, `false` and `failure`. Read them from the umbrella that still owns metadata.

## Outputs

| Output | Values | Description |
|--------|--------|-------------|
| `has_breaking_changes` | `true` / `false` | Whether the PR contains at least one breaking-change commit |
| `breaking_change_approved` | `true` / `false` | Whether the PR description contains the exact acknowledgement |
| `breaking_change_result` | `success` / `failure` | Normalized guard result used by the nested `Blocking Checks` job |

These outputs forward the nested `pr-validation` job outputs with fail-closed fallbacks at the umbrella boundary: an absent nested value becomes `false`, `false`, and `failure`, respectively.

## Breaking Change Guard

When a PR contains a breaking change, its description must contain this exact, case-sensitive line:

```text
Breaking change acknowledged: I understand that this PR intentionally introduces a breaking change and requires the next release to be a major version.
```

The guard is mandatory for every PR target branch whenever the metadata pipeline runs (see `run_metadata`). PRs without the required acknowledgement fail in the existing `Blocking Checks` job, including drafts. `dry_run: true` reports detection and approval without enforcing the guard.

Caller triggers must include the five activity types in the usage example. `edited` is mandatory so removing or adding the acknowledgement reruns validation. `ready_for_review` is retained for complete validation transitions even though the guard enforces drafts.

## Permission Manifest Nudge (RI) — non-blocking

Part of the Access-Manager **Inversão de Responsabilidade (RI)** rollout. The `permission-manifest-nudge` job reminds a plugin/service to declare its permissions in a `permissions.yaml` manifest instead of relying on manual Access-Manager configuration.

- **Scope gate:** only acts when `go.mod` has a **direct** dependency on `github.com/LerianStudio/lib-auth`. Repos with no `go.mod` or no direct lib-auth dependency are skipped silently. (This is the intended scoping — tune the `grep` in the composite to widen or narrow it.)
- **Presence check:** globs every `permissions.yaml` (excluding `vendor/`, `node_modules/`, `.git/`) and only counts files with top-level `service:` **and** `permissions:` keys.
- **Idempotent comment:** posts / updates a single find-by-marker (`<!-- permission-manifest-nudge -->`) sticky comment — never spams per push. When a manifest is present it flips any prior nudge to a positive state.
- **Never blocks:** the job runs with `continue-on-error: true`, the composite always exits 0, and there is **no** `*-gate` aggregator for it — so it must **not** be added to branch protection. Disable it entirely with `run_manifest_nudge: false`.

See [`src/validate/permission-manifest-nudge`](../src/validate/permission-manifest-nudge/README.md) for the composite action details.

## Secrets

| Secret | Description | Required |
|--------|-------------|----------|
| `MANAGE_TOKEN` | Token for private Go module access and PR operations | No |
| `SLACK_WEBHOOK_URL` | Slack webhook for pipeline notifications | No |
| `LERIAN_LIB_READ_TOKEN` | Read token for private Lerian libs in the lib version check (falls back to `GITHUB_TOKEN`) | No |

## Usage

```yaml
name: PR Validation
on:
  pull_request:
    types: [opened, edited, synchronize, reopened, ready_for_review]

permissions:
  actions: read
  contents: read
  id-token: write
  issues: write
  pull-requests: write
  security-events: write

jobs:
  validate:
    # Testing: @develop or @feat/<branch> · Production: pinned @vX.Y.Z
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-pr-validation.yml@tier-1
    with:
      go_version: "1.26.4"
      golangci_lint_version: "v2.12.2"
      coverage_threshold: 79
      fail_on_coverage_threshold: true
      go_private_modules: "github.com/LerianStudio/*"
      ignore_file: ".trivyignore.yaml"
      shared_paths: |
        go.mod
        go.sum
        internal/
        pkg/
        migrations/
        Dockerfile
        Makefile
    secrets: inherit
```

## Branch protection

Require the aggregator checks `Go Analysis`, `Security` and `Lib Version` (plus the PR metadata checks from `pr-validation.yml`). Breaking-change enforcement remains inside the existing `Blocking Checks` status; it does not add a branch-protection check. These names are stable even when the underlying analysis matrix changes.

## Related

- [go-pr-analysis](./go-pr-analysis-workflow.md) — the Go analysis pipeline this umbrella calls
- [pr-security-scan](./pr-security-scan-workflow.md) — the security pipeline this umbrella calls
- [pr-validation](./pr-validation.md) — the PR metadata validation this umbrella calls
- [go-release](./go-release-workflow.md) — the matching service release umbrella
