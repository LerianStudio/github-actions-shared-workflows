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
5. **Socket supply chain** — blocks malicious packages at install time and, optionally, runs the full Socket CLI report (`src/security/socket-firewall`, `src/security/socket-scan`). Enabled by default; disable with `run_socket: false`.

The `frontend-analysis`, `security` and `socket` pipelines each have a `*-gate` aggregator job that exposes a single stable status-check name (`Frontend Analysis`, `Security`, `Socket`) for branch protection, regardless of the internal job names. All are gated by the change detector, so documentation-only PRs skip them (and the aggregators still report success). If the change detector (`changes`) job itself fails, the aggregators propagate that failure instead of passing.

## Inputs

| Input | Description | Type | Default |
|-------|-------------|------|---------|
| `runner_type` | GitHub runner type | string | `blacksmith-4vcpu-ubuntu-2404` |
| `dry_run` | Preview metadata validations without posting comments/labels | boolean | `false` |
| `run_frontend_analysis` | Run the frontend analysis pipeline | boolean | `true` |
| `run_security` | Run the security scan pipeline | boolean | `true` |
| `run_socket` | Run the Socket supply-chain pipeline | boolean | `true` |
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
| `filter_paths` | JSON array of paths to monitor for changes (e.g. `["ui"]`), passed through to `frontend-pr-analysis.yml` only | string | `''` |
| `shared_paths` | Newline-separated path patterns that trigger analysis for ALL components in `filter_paths`, passed through to `frontend-pr-analysis.yml` only | string | `''` |
| `path_level` | Directory depth level to extract app name, passed through to `frontend-pr-analysis.yml` only | number | `2` |
| `normalize_to_filter` | Collapse every changed file under a `filter_paths` entry into that one app, passed through to `frontend-pr-analysis.yml` only | boolean | `true` |
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
| `enable_bundle_budget` | Enable a bundle-size budget check (runs `bundle_budget_script`) | boolean | `false` |
| `bundle_budget_script` | npm script that enforces the bundle-size budget | string | `check:bundle-budget` |
| `enable_performance_budget` | Enable a performance budget check (runs `performance_budget_script`) | boolean | `false` |
| `performance_budget_script` | npm script that enforces the performance budget | string | `check:performance` |
| `enable_visual_regression` | Enable visual regression testing (runs `visual_regression_script`) | boolean | `false` |
| `visual_regression_script` | npm script that runs visual regression tests | string | `test:visual` |
| `enable_docker_smoke` | Enable a Docker image smoke test (build, run, poll health endpoint) | boolean | `false` |
| `docker_smoke_dockerfile_path` | Path to the Dockerfile for the smoke test. Empty = `<working_dir>/Dockerfile` | string | `''` |
| `docker_smoke_build_args` | Newline-separated Docker build args for the smoke-test image | string | `''` |
| `docker_smoke_port` | Container port to publish and probe for the smoke test | number | `3000` |
| `docker_smoke_health_path` | HTTP path polled on the running container to confirm startup | string | `/health` |
| `docker_smoke_timeout` | Seconds to wait for the health check before failing the smoke test | number | `60` |
| `docker_smoke_test_script` | npm script run against the running container after the health check passes | string | `''` |
| `docker_smoke_env` | Newline-separated runtime env vars passed to `docker run`, distinct from `docker_smoke_build_args` | string | `''` |
| `enable_accessibility` | Enable an accessibility check (runs `accessibility_script`) | boolean | `false` |
| `accessibility_script` | npm script that runs accessibility tests | string | `test:a11y` |
| `enable_custom_checks` | Enable arbitrary caller-owned checks beyond the named gates above (runs each script in `custom_checks`) | boolean | `false` |
| `custom_checks` | Newline-separated npm script names to run as additional checks | string | `''` |
| `custom_checks_needs_browsers` | Install Playwright browsers before running `custom_checks` | boolean | `false` |
| `prerelease_block_branches` | Target branches where pre-release versions are hard failures (comma-separated) | string | `release-candidate,main` |
| `enable_docker_scan` | Build and scan a Docker image with Trivy; set `false` for repos without a Dockerfile (CLIs, libraries) | boolean | `true` |
| `dockerfile_path` | Explicit path to a single Dockerfile to build and scan (e.g. `Dockerfile`) | string | `''` |
| `enable_codeql` | Enable CodeQL static analysis | boolean | `false` |
| `codeql_languages` | CodeQL languages (comma-separated, e.g. `javascript-typescript`) | string | `''` |
| `ignore_file` | Path to Trivy ignore file (e.g. `.trivyignore.yaml`) | string | `''` |
| `trivy_skip_dirs` | Comma-separated directories to skip in every Trivy filesystem scan | string | `''` |
| `socket_enable_firewall` | Run Socket Firewall (free tier, no token) and install dependencies through it | boolean | `true` |
| `socket_enable_scan` | Run the Socket CLI scan (paid tier, needs `SOCKET_SECURITY_API_KEY`) | boolean | `false` |
| `socket_working_dir` | Directory holding the `package.json` and lockfile scanned by the Socket job | string | `.` |
| `socket_firewall_version` | Socket Firewall binary version | string | `latest` |
| `socket_job_summary` | Socket Firewall job summary verbosity (`all`, `errors`, `none`) | string | `all` |
| `socket_use_cache` | Cache the Socket Firewall binaries between runs (the `sfw` binary only) | boolean | `true` |
| `socket_fail_on_block` | Fail the Socket job when Socket Firewall blocks a package | boolean | `true` |
| `socket_fail_on_findings` | Fail the Socket job when the Socket CLI scan reports blocking alerts | boolean | `false` |
| `socket_sarif_file` | Path where the Socket CLI scan writes its SARIF report (empty = none) | string | `''` |
| `socket_ignore_commit_files` | Scan every manifest instead of only the ones touched by the commit | boolean | `false` |
| `socket_python_version` | Python version used to run the Socket CLI | string | `3.12` |
| `socket_cli_version` | `socketsecurity` release installed from PyPI (pinned; `latest` tracks the newest) | string | `2.5.8` |

> **Monorepo note:** `filter_paths`/`shared_paths`/`path_level`/`normalize_to_filter` scope the `frontend-analysis` job only. They are not passed to the `security` job because `frontend-pr-analysis.yml` and `pr-security-scan.yml` use different formats for that input (JSON array vs. newline-separated). For a path-scoped security scan too, call `pr-security-scan.yml` directly.

## Secrets

| Secret | Description | Required |
|--------|-------------|----------|
| `MANAGE_TOKEN` | Token for PR operations and private package access | No |
| `SLACK_WEBHOOK_URL` | Slack webhook for pipeline notifications | No |
| `SOCKET_SECURITY_API_KEY` | Socket API token for the Socket CLI scan (paid tier). Absent = the scan skips with a notice | No |

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

## Socket supply chain

`npm audit`, Trivy and CodeQL find known CVEs and insecure code. None of them find a **supply-chain attack** — a package with a malicious install script, a typosquat, a dependency hijacked in a patch release. [Socket](https://socket.dev) covers that gap by analyzing package behavior, and it is wired here in two independent layers.

> Not to be confused with `socket.io`, the WebSocket library. Unrelated project, no scanning capability.

### Free tier — Socket Firewall (on by default)

[`src/security/socket-firewall`](../src/security/socket-firewall/README.md) installs Socket Firewall's free edition, which shims `npm`/`yarn`/`pnpm`, then runs the project's install through it. A malicious package makes the install exit non-zero and the `Socket` check goes red. No token, no account, no cost.

The shim only protects installs in the same job, so this runs a clean install of the same lockfile in the dedicated `socket` job. The 12 install steps inside `frontend-pr-analysis.yml` are not shimmed — the gate here is what blocks the PR.

**Monorepos:** the install needs a lockfile in `socket_working_dir` (default `.`). If none is found the layer skips with a warning instead of failing, so point it at the right directory:

```yaml
with:
  socket_working_dir: 'ui'
```

Unlike `filter_paths`, this is a single directory — the Socket job is not matrixed per component. Repositories with several independently-locked apps should call the composite directly from their own matrixed job.

To report blocks as warnings instead of failing:

```yaml
with:
  socket_fail_on_block: false
```

An install that fails for an ordinary reason (bad lockfile, unreachable registry) always fails the job — `socket_fail_on_block` only softens confirmed Socket blocks.

### Paid tier — Socket CLI scan (off by default)

[`src/security/socket-scan`](../src/security/socket-scan/README.md) runs `socketcli`, which posts the full alert report on the PR and enforces the organization's Socket policy. It needs the `SOCKET_SECURITY_API_KEY` secret; **without the secret it skips with a `::notice::` and the job stays green**, so enabling it early breaks nothing.

```yaml
with:
  socket_enable_scan: true          # opt-in
  socket_fail_on_findings: false    # default — advisory until the repo is clean
secrets: inherit                    # carries SOCKET_SECURITY_API_KEY
```

Socket API errors (`exit 3`) and unmet reachability prerequisites (`exit 5`) are always advisory — they say nothing about the dependencies under review.

### Turning the whole thing off

```yaml
with:
  run_socket: false
```

## Branch protection

Require the aggregator checks `Frontend Analysis`, `Security` and `Socket` (plus the PR metadata checks from `pr-validation.yml`). These names are stable even when the underlying analysis steps change.

## Related

- [frontend-pr-analysis](./frontend-pr-analysis-workflow.md) — the frontend analysis pipeline this umbrella calls
- [pr-security-scan](./pr-security-scan-workflow.md) — the security pipeline this umbrella calls
- [pr-validation](./pr-validation.md) — the PR metadata validation this umbrella calls
- [go-pr-validation](./go-pr-validation.md) — the equivalent umbrella for Go repositories
