<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>js-pr-validation</h1></td>
  </tr>
</table>

Umbrella reusable workflow for JavaScript/TypeScript repositories. A caller references this single workflow and it orchestrates everything a JS/TS PR needs:

1. **PR metadata** — title, source branch, size, labels (delegates to `pr-validation.yml`).
2. **Change gate** — detects whether the PR touches anything beyond docs/meta (`src/config/non-doc-changes`); documentation-only PRs skip the heavy pipelines.
3. **Frontend analysis** — lint, typecheck, npm audit, tests, coverage and build (delegates to `frontend-pr-analysis.yml`), opt-in via `run_frontend_analysis`.
4. **Security scan** — Trivy, CodeQL, prerelease checks (delegates to `pr-security-scan.yml`), opt-in via `run_security`.

The `frontend-analysis` and `security` pipelines each have a `*-gate` aggregator job that exposes a single stable status-check name (`Frontend Analysis`, `Security`) for branch protection, regardless of the internal job names. Both are gated by the change detector, so documentation-only PRs skip them (and the aggregators still report success). If the change detector (`changes`) job itself fails, the aggregators propagate that failure instead of passing.

## Inputs

| Input | Description | Type | Default |
|-------|-------------|------|---------|
| `runner_type` | GitHub runner type | string | `blacksmith-4vcpu-ubuntu-2404` |
| `dry_run` | Preview metadata validations without posting comments/labels | boolean | `false` |
| `run_frontend_analysis` | Run the frontend analysis pipeline | boolean | `true` |
| `run_security` | Run the security scan pipeline | boolean | `true` |
| `ignore_globs` | Space-separated globs treated as docs/meta for the change gate | string | `*.md docs/* .github/* LICENSE* .gitignore` |
| `pr_title_types` | Allowed commit types (pipe-separated) | string | `feat\|fix\|docs\|style\|refactor\|perf\|test\|chore\|ci\|build\|revert` |
| `pr_title_scopes` | Allowed scopes (pipe-separated, empty = any) | string | `''` |
| `require_scope` | Require scope in PR title | boolean | `false` |
| `enable_auto_labeler` | Auto-label by changed files | boolean | `true` |
| `labeler_config_path` | Path to labeler config | string | `.github/labeler.yml` |
| `enforce_source_branches` | Enforce source branches into protected branches | boolean | `true` |
| `allowed_source_branches` | Allowed source branches (pipe-separated, `*` prefix) | string | `develop\|release-candidate\|hotfix/*` |
| `target_branches_for_source_check` | Target branches requiring source validation | string | `main` |
| `node_version` | Node.js version | string | `22` |
| `package_manager` | Package manager (`npm`, `yarn`, `pnpm`) | string | `npm` |
| `eslint_args` | Additional arguments for ESLint | string | `''` |
| `audit_level` | npm audit severity level (`low`, `moderate`, `high`, `critical`) | string | `high` |
| `coverage_threshold` | Minimum coverage percentage (0-100) | number | `80` |
| `fail_on_coverage_threshold` | Fail when coverage is below threshold | boolean | `false` |
| `app_name_prefix` | Prefix used to namespace coverage/build artifacts | string | `''` |
| `enable_lint` | Enable ESLint | boolean | `true` |
| `enable_typecheck` | Enable TypeScript type checking | boolean | `true` |
| `enable_security` | Enable npm audit | boolean | `true` |
| `enable_tests` | Enable unit tests | boolean | `true` |
| `enable_coverage` | Enable coverage check with PR comment | boolean | `true` |
| `enable_build` | Enable build verification | boolean | `true` |
| `enable_i18n_check` | Enable i18n key validation | boolean | `false` |
| `i18n_check_script` | npm script for extraction-parity check | string | `check:i18n` |
| `i18n_keys_check_script` | npm script for locale-parity check | string | `check:i18n:keys` |
| `i18n_check_fail_on_violation` | Fail when any i18n check reports violations | boolean | `true` |
| `prerelease_block_branches` | Target branches where pre-release versions are hard failures (comma-separated) | string | `release-candidate,main` |
| `enable_docker_scan` | Build and scan a Docker image with Trivy; set `false` for repos without a Dockerfile (CLIs, libraries) | boolean | `true` |
| `dockerfile_path` | Explicit path to a single Dockerfile to build and scan (e.g. `Dockerfile`) | string | `''` |
| `enable_codeql` | Enable CodeQL static analysis | boolean | `false` |
| `codeql_languages` | CodeQL languages (comma-separated, e.g. `javascript-typescript`) | string | `''` |
| `ignore_file` | Path to Trivy ignore file (e.g. `.trivyignore.yaml`) | string | `''` |
| `trivy_skip_dirs` | Comma-separated directories to skip in every Trivy filesystem scan | string | `''` |

> **Monorepo note:** `filter_paths` is not exposed at the umbrella level because `frontend-pr-analysis.yml` and `pr-security-scan.yml` use different formats for that input. For monorepo setups with per-component scanning, call the individual primitives directly.

## Secrets

| Secret | Description | Required |
|--------|-------------|----------|
| `MANAGE_TOKEN` | Token for PR operations and private package access | No |
| `SLACK_WEBHOOK_URL` | Slack webhook for pipeline notifications | No |

All other secrets required by the underlying primitives (e.g. `DOCKER_USERNAME`, `DOCKERHUB_IMAGE_PULL_TOKEN`, `NPMRC_TOKEN`) are forwarded automatically via `secrets: inherit`.

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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/js-pr-validation.yml@v1
    with:
      app_name_prefix: "lerian-map"
      coverage_threshold: 85
      pr_title_scopes: |
        components
        pages
        hooks
        lib
        api
    secrets: inherit
```

### NestJS backend (no Docker)

```yaml
jobs:
  validate:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/js-pr-validation.yml@v1
    with:
      enable_docker_scan: false
      coverage_threshold: 80
      fail_on_coverage_threshold: true
    secrets: inherit
```

### TypeScript library (no Docker, no build step)

```yaml
jobs:
  validate:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/js-pr-validation.yml@v1
    with:
      enable_docker_scan: false
      enable_build: false
      coverage_threshold: 90
      fail_on_coverage_threshold: true
    secrets: inherit
```

## Branch protection

Require the aggregator checks `Frontend Analysis` and `Security` (plus the PR metadata checks from `pr-validation.yml`). These names are stable even when the underlying analysis steps change.

## Related

- [frontend-pr-analysis](./frontend-pr-analysis-workflow.md) — the frontend analysis pipeline this umbrella calls
- [pr-security-scan](./pr-security-scan-workflow.md) — the security pipeline this umbrella calls
- [pr-validation](./pr-validation.md) — the PR metadata validation this umbrella calls
- [go-pr-validation](./go-pr-validation.md) — the equivalent umbrella for Go repositories
