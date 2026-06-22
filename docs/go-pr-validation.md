<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>go-pr-validation</h1></td>
  </tr>
</table>

Umbrella reusable workflow for Go service repositories. A caller references this single workflow and it orchestrates everything a Go service PR needs:

1. **PR metadata** — title, source branch, size, labels (delegates to `pr-validation.yml`).
2. **Change gate** — detects whether the PR touches anything beyond docs/meta (`src/config/non-doc-changes`); documentation-only PRs skip the heavy pipelines.
3. **Go analysis** — lint, tests, coverage and build (delegates to `go-pr-analysis.yml`), opt-in via `run_go_analysis`.
4. **Security scan** — Trivy, CodeQL, prerelease checks (delegates to `pr-security-scan.yml`), opt-in via `run_security`.
5. **Lerian lib version check** — fails when a direct Lerian library is behind its latest stable release (delegates to `lerian-lib-version-check.yml`), opt-in via `run_lib_version_check`.

The `go-analysis`, `security` and `lib-version` pipelines each have a `*-gate` aggregator job that exposes a single stable status-check name (`Go Analysis`, `Security`, `Lib Version`) for branch protection, regardless of the internal job names. All three are gated by the change detector, so documentation-only PRs skip them (and the aggregators still report success). If the change detector (`changes`) job itself fails, the aggregators propagate that failure instead of passing — so broken change detection cannot let the required checks go green.

## Inputs

| Input | Description | Type | Default |
|-------|-------------|------|---------|
| `runner_type` | GitHub runner type | string | `blacksmith-4vcpu-ubuntu-2404` |
| `dry_run` | Preview metadata validations without posting comments/labels | boolean | `false` |
| `run_go_analysis` | Run the Go analysis pipeline | boolean | `true` |
| `run_security` | Run the security scan pipeline | boolean | `true` |
| `run_lib_version_check` | Run the Lerian library version check | boolean | `true` |
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
| `go_version` | Go version | string | `1.23` |
| `golangci_lint_version` | GolangCI-Lint version | string | `v1.62.2` |
| `golangci_lint_args` | Extra arguments passed to golangci-lint (e.g. `--timeout=5m`) | string | `--timeout=5m` |
| `app_name_prefix` | Prefix used to namespace coverage/build artifacts | string | `''` |
| `filter_paths` | Newline-separated component path prefixes for monorepo per-component analysis (lint/tests/coverage); empty = single-app root analysis | string | `''` |
| `path_level` | Directory depth level to extract the component name from `filter_paths` | number | `2` |
| `coverage_threshold` | Minimum coverage percentage (0-100) | number | `80` |
| `fail_on_coverage_threshold` | Fail when coverage is below threshold | boolean | `true` |
| `go_private_modules` | GOPRIVATE pattern for private modules | string | `''` |
| `enable_integration_tests` | Enable integration tests | boolean | `false` |
| `system_packages` | apt packages to install for CGO repos | string | `''` |
| `ignore_file` | Path to Trivy ignore file | string | `''` |
| `enable_docker_scan` | Build and scan a Docker image with Trivy; set `false` for repos without a root Dockerfile (monorepos with Dockerfiles under `components/`/`cmd/`) | boolean | `true` |
| `dockerfile_path` | Explicit path to a single Dockerfile to build and scan (e.g. `components/ledger/Dockerfile`); lets monorepos without a root Dockerfile keep `enable_docker_scan: true` | string | `''` |
| `enable_codeql` | Enable CodeQL static analysis | boolean | `false` |
| `codeql_languages` | CodeQL languages (comma-separated) | string | `''` |
| `shared_paths` | Path patterns that trigger analysis/security for all components | string | `''` |

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
    branches: [develop, release-candidate, main]
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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-pr-validation.yml@v1
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

Require the aggregator checks `Go Analysis`, `Security` and `Lib Version` (plus the PR metadata checks from `pr-validation.yml`). These names are stable even when the underlying analysis matrix changes.

## Related

- [go-pr-analysis](./go-pr-analysis-workflow.md) — the Go analysis pipeline this umbrella calls
- [pr-security-scan](./pr-security-scan-workflow.md) — the security pipeline this umbrella calls
- [pr-validation](./pr-validation.md) — the PR metadata validation this umbrella calls
- [go-release](./go-release-workflow.md) — the matching service release umbrella
