<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>js-pr-validation</h1></td>
  </tr>
</table>

Umbrella reusable workflow for JavaScript/TypeScript repositories. A caller references this single workflow and it orchestrates everything a JS/TS PR needs:

1. **PR metadata** — title, source branch, size, labels (delegates to `pr-validation.yml`).
2. **Breaking Change Guard** — mandatory detection and enforcement inherited from `pr-validation.yml` for every PR target branch, whenever the metadata pipeline runs (see `run_metadata`).
3. **Change gate** — detects whether the PR touches anything beyond docs/meta (`src/config/non-doc-changes`); documentation-only PRs skip the heavy pipelines.
4. **Frontend analysis** — lint, typecheck, npm audit, tests, coverage and build (delegates to `frontend-pr-analysis.yml`). Enabled by default; disable with `run_frontend_analysis: false`.
5. **Security scan** — Trivy, CodeQL, prerelease checks (delegates to `pr-security-scan.yml`). Enabled by default; disable with `run_security: false`.
6. **Socket supply chain** — refuses malicious packages at install time, turns the Socket App's advisory verdict into an enforceable check, and reports per-package findings split into what this pull request introduced and what the tree already carried. Enabled by default; disable with `run_socket: false`.

The `frontend-analysis`, `security` and `socket` pipelines each have a `*-gate` aggregator job that exposes a single stable status-check name (`Frontend Analysis`, `Security`, `Socket`) for branch protection, regardless of the internal job names. All are gated by the change detector, so documentation-only PRs skip them (and the aggregators still report success). If the change detector (`changes`) job itself fails, the aggregators propagate that failure instead of passing.

## Inputs

| Input | Description | Type | Default |
|-------|-------------|------|---------|
| `runner_type` | GitHub runner type | string | `blacksmith-4vcpu-ubuntu-2404` |
| `build_runner_type` | Optional runner override for the frontend analysis Build jobs only; empty falls back to `vars.GENERAL_RUNNERS`, then `runner_type` | string | `''` |
| `custom_checks_runner_type` | Optional runner override for the frontend analysis Custom Checks jobs only; empty falls back to `vars.GENERAL_RUNNERS`, then `runner_type` | string | `''` |
| `security_scan_runner_type` | Optional runner override for the `security_scan` jobs only; empty falls back to `vars.GENERAL_RUNNERS`, then `runner_type` | string | `''` |
| `dry_run` | Preview metadata validations without posting comments/labels | boolean | `false` |
| `run_metadata` | Run the PR metadata pipeline (title, scopes, labeler, size, breaking-change guard). Set `false` in a multi-component repository that also calls `go-pr-validation.yml`, so exactly one umbrella owns PR metadata | boolean | `true` |
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
| `require_verified_commits` | Block the PR when any commit is unsigned or unverified | boolean | `true` |
| `node_version` | Node.js version | string | `22` |
| `package_manager` | Package manager (`npm`, `yarn`, `pnpm`) | string | `npm` |
| `eslint_args` | Additional arguments for ESLint | string | `''` |
| `audit_level` | npm audit severity level (`low`, `moderate`, `high`, `critical`) | string | `high` |
| `coverage_threshold` | Minimum coverage percentage (0-100) | number | `80` |
| `fail_on_coverage_threshold` | Fail when coverage is below threshold | boolean | `false` |
| `filter_paths` | JSON array of paths to monitor for changes (e.g. `["ui"]`), passed through to `frontend-pr-analysis.yml`. The security scan uses `security_filter_paths` instead | string | `''` |
| `shared_paths` | Newline-separated path patterns that trigger analysis for ALL components in `filter_paths`, passed through to `frontend-pr-analysis.yml`. The security scan uses `security_shared_paths` instead | string | `''` |
| `path_level` | Directory depth level to extract app name; passed through to **both** `frontend-pr-analysis.yml` and `pr-security-scan.yml` | number | `2` |
| `normalize_to_filter` | Collapse every changed file under a `filter_paths` entry into that one app; passed through to **both** `frontend-pr-analysis.yml` and `pr-security-scan.yml` | boolean | `true` |
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
| `security_filter_paths` | Newline-separated component path prefixes for a path-scoped security scan (e.g. `components/ui`). Separate from `filter_paths` because the two callees use different formats. Empty = single-app root scan | string | `''` |
| `security_shared_paths` | Newline-separated path patterns that trigger the security scan for ALL components in `security_filter_paths` | string | `''` |
| `build_context_from_working_dir` | Build each component image with its own `working_dir` as the Docker build context instead of the repository root. Required for monorepos whose components are independent packages | boolean | `false` |
| `enable_codeql` | Enable CodeQL static analysis | boolean | `false` |
| `codeql_languages` | CodeQL languages (comma-separated, e.g. `javascript-typescript`) | string | `''` |
| `ignore_file` | Path to Trivy ignore file (e.g. `.trivyignore.yaml`) | string | `''` |
| `trivy_skip_dirs` | Comma-separated directories to skip in every Trivy filesystem scan | string | `''` |
| `socket_enable_firewall` | Run Socket Firewall (free tier, no token) and install dependencies through it | boolean | `true` |
| `socket_working_dir` | Directory holding the `package.json` and lockfile scanned by the Socket job | string | `.` |
| `socket_firewall_version` | Socket Firewall binary version | string | `latest` |
| `socket_job_summary` | Socket Firewall job summary verbosity (`all`, `errors`, `none`) | string | `all` |
| `socket_use_cache` | Cache the Socket Firewall binaries between runs (the `sfw` binary only) | boolean | `true` |
| `socket_fail_on_block` | Fail the Socket job when Socket Firewall blocks a package | boolean | `true` |
| `socket_enable_app_gate` | Turn the Socket GitHub App checks into an enforceable gate (no token needed) | boolean | `true` |
| `socket_app_slug` | GitHub App slug whose checks the gate reads | string | `socket-security` |
| `socket_app_timeout` | Seconds to wait for the App checks before treating the result as inconclusive | number | `300` |
| `socket_app_fail_on_findings` | Fail the Socket job when the App reports adverse checks | boolean | `true` |
| `socket_app_on_inconclusive` | `block` or `warn` when the App reached no verdict | string | `block` |
| `socket_app_on_missing` | `warn` or `block` when the App published no checks | string | `warn` |
| `enable_coderabbit_gate` | Hold CodeRabbit until this validation passes. Requires setup in the consuming repo — see [coderabbit-gate](coderabbit-gate.md) | boolean | `false` |
| `coderabbit_review_base_branches` | Comma-separated exact base branch names whose PRs get a review. Empty removes this dimension | string | `develop` |
| `coderabbit_review_head_patterns` | Comma-separated globs matched against the head branch; a match is reviewed regardless of base | string | `hotfix/*` |
| `coderabbit_gate_label` | Trigger label. Must match `reviews.auto_review.labels` in `.coderabbit.yml` | string | `review-ready` |
| `socket_enable_api_report` | Read the App's full scan and report per-package alerts, vulnerabilities and scores (advisory) | boolean | `true` |
| `socket_api_max_rows` | Maximum package rows per findings section | number | `25` |
| `socket_api_include_actions` | Socket alert actions reported as findings | string | `error,warn,monitor` |
| `socket_api_fail_on_actions` | Actions that block the PR — **introduced findings only**. Empty blocks nothing | string | `''` |
| `socket_comment_when` | `findings` posts the comment only when there is something to act on; `always` posts every run | string | `findings` |

> **Monorepo note:** `filter_paths` scopes the `frontend-analysis` job; `security_filter_paths` scopes the `security` job. They are separate inputs because the two callees expect different formats — `frontend-pr-analysis.yml` takes a JSON array, `pr-security-scan.yml` takes a newline-separated list. `path_level` and `normalize_to_filter` are shared by both. Set `build_context_from_working_dir: true` when each component Dockerfile expects its own directory as build context.

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

The guard is mandatory for every PR target branch. PRs without the required acknowledgement fail in the existing `Blocking Checks` job, including drafts. `dry_run: true` reports detection and approval without enforcing the guard.

Caller triggers must include the five activity types in the usage example. `edited` is mandatory so removing or adding the acknowledgement reruns validation. `ready_for_review` is retained for complete validation transitions even though the guard enforces drafts.

## Secrets

| Secret | Description | Required |
|--------|-------------|----------|
| `MANAGE_TOKEN` | Token for PR operations and private package access | No |
| `SLACK_WEBHOOK_URL` | Slack webhook for pipeline notifications | No |
| `SOCKET_SECURITY_API_KEY` | Socket API token for the Socket API Report step. Scopes: `full-scans:list`, `diff-scans:list`, `diff-scans:create`. Absent, that step skips with a notice and the other Socket layers keep working | No |

All other secrets required by the underlying primitives (e.g. `DOCKER_USERNAME`, `DOCKERHUB_IMAGE_PULL_TOKEN`, `NPMRC_TOKEN`) are forwarded automatically via `secrets: inherit`.

## Usage

```yaml
name: PR Validation
on:
  pull_request:
    types: [opened, edited, synchronize, reopened, ready_for_review]

permissions:
  actions: read
  checks: read          # required by the Socket App gate
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

`npm audit`, Trivy and CodeQL find known CVEs and insecure code. None of them find a **supply-chain attack** — a package with a malicious install script, a typosquat, a dependency hijacked in a patch release. [Socket](https://socket.dev) covers that gap by analyzing package behavior, and it is wired here in three layers that do different jobs: one refuses the install, one turns the App's verdict into a gate, and one reports the findings per package.

> Not to be confused with `socket.io`, the WebSocket library. Unrelated project, no scanning capability.

### Layer 1 — Socket Firewall, on every install

[`setup-node-guarded`](../src/setup/setup-node-guarded/README.md) installs Socket Firewall's free edition (no token, no account) and runs `sfw npm ci` — or the `yarn`/`pnpm` equivalent — instead of a bare install. A malicious package is refused mid-fetch, so it is never written to disk and its install scripts never run.

This applies to **every** install in the pipeline: all twelve analysis jobs in `frontend-pr-analysis.yml` plus the dedicated `socket` job. That breadth is the point. A firewall shim only protects installs in its own job, so guarding one job would leave the others executing `postinstall` scripts with the runner's tokens in scope.

Two consequences worth knowing:

- **No package-manager cache on guarded installs.** Socket Firewall only sees what crosses the network; per its docs, *"if there are no network requests, as is the case when artifacts are cached locally, there is nothing for `sfw` to block"*. So `cache:` is not passed to `actions/setup-node` and the cache is purged before each install. Measured cost is small — a cold `sfw npm ci` over ~2000 packages takes about 20s.
- **No private registries.** The free edition does not support custom registries. A repository that needs one must set `socket_enable_firewall: false`, which restores the previous behaviour, cache included.

```yaml
with:
  socket_enable_firewall: true   # default
  socket_fail_on_block: false    # report blocks as warnings instead of failing
```

An install that fails for an ordinary reason always fails the job — `socket_fail_on_block` only softens confirmed Socket blocks.

### Layer 2 — Socket App gate, no token required

The organization already runs the [Socket GitHub App](https://github.com/marketplace/socket-security), which analyses the dependency graph and posts `Socket Security: Project Report` and `Socket Security: Pull Request Alerts`. What it does not do is enforce: its checks land as `success`, `neutral` or `skipped`, and neither `neutral` nor `skipped` blocks a merge.

[`socket-app-gate`](../src/security/socket-app-gate/README.md) waits for those checks on the PR **head** SHA and converts them into a verdict this workflow owns. It re-scans nothing, needs no API token and consumes no Socket quota — running `socketcli` in CI instead would duplicate the same analysis and post a second, competing report.

| Verdict | Meaning | Default |
|---|---|---|
| `pass` | Every App check completed non-adversely | Passes |
| `findings` | A check concluded `failure`/`action_required`/`cancelled`/`timed_out` | **Blocks** |
| `inconclusive` | Checks exist but are `neutral`/`skipped`, or the wait timed out | **Blocks** |
| `missing` | The App published no checks — it is not installed here | Warns |

`inconclusive` blocking is deliberate. On a pull request with merge conflicts the App reports *"Skipped un-mergeable pull request"*, meaning no diff was analysed at all — treating that as clean would wave through exactly the wrong pull request. `missing` only warns, so repositories without the App stay green and rely on layer 1.

```yaml
with:
  socket_app_on_inconclusive: 'warn'   # default 'block'
  socket_app_on_missing: 'block'       # default 'warn' — require the App
```

### Layer 3 — Dependency findings

The first two layers answer narrow questions. The firewall reports what it **refused**, never what it allowed. The App's checks carry a status and a dashboard link — `Project Report`'s `output.text` is literally `null`. Neither can say *which package has which problem, and whether this pull request caused it*.

[`socket-api-report`](../src/security/socket-api-report/README.md) closes that. It reads the scan Socket already computed for the commit, plus the diff scan the App computed for the pull request, and reports per-package findings split by origin.

**Filtering.** Measured on a real 1897-package tree: of 4636 alerts, `ignore` accounted for 4594 and only 42 carried an action. Severity is not a usable filter — 118 alerts were `high` and still ignored. Capabilities like `envVars` or `networkAccess` are normal in isolation; Socket has already judged them by the time it assigns an action, so action is the axis used here.

**Attribution, and why it matters for gating.** `socket_api_fail_on_actions` applies **only to findings this pull request introduces**. On `product-console` the tree already carries 43 actioned findings; gating on those would fail every pull request in the repository for something none of them caused, and the gate would be switched off within a week. Pre-existing findings are collapsed into a `<details>` and never block.

**Provenance.** Transitive findings name the direct dependency that reaches them — `oauth@0.9.15` reads as `via next-auth`, because `oauth` is nobody's decision and `next-auth` is. Coverage on the reference tree was 1755 of 1897 artifacts; the rest are direct dependencies, which have no ancestor.

**Scopes.** `full-scans:list`, `diff-scans:list` and `diff-scans:create` on `SOCKET_SECURITY_API_KEY` — the last one covers the diff the layer rebuilds when Socket has not diffed this commit's scan. Without the token the layer skips with a notice.

**Not previewable.** This layer does not run under `dry_run: true`: resolving attribution can create a diff scan on the Socket organization, which is the side effect a preview must not have. The dry-run notice therefore reports the blocking count as *not computed* rather than as zero — a number nobody measured is not a clean result.

**Advisory by construction.** Every API failure path exits `0` and reports zero blocking findings. A Socket outage or an exhausted quota must never read as a security finding — enforcement stays with layer 2's verdict, layer 1's refusal to install, and `socket_api_fail_on_actions` when a repository opts in.

```yaml
with:
  socket_api_fail_on_actions: 'error'   # default '' — report only
  socket_api_include_actions: 'error,warn'
```

> **Known coupling.** The diff scan id is read from the Socket App's own pull request comment: looking it up by `after_full_scan_id` returns nothing, because the App diffs against a different full scan than the one its `Project Report` check links to. Disabling the App's comments therefore breaks attribution — everything reverts to pre-existing and `socket_api_fail_on_actions` goes inert, silently.

### The PR comment

One upserted comment per pull request, under `<!-- socket-supply-chain-<app> -->`, carrying **findings only**. Whether the scan ran, which App checks passed and how many alerts were filtered out live in the job log and in the `Socket` status check — see [`socket-reporter`](../src/security/socket-reporter/README.md).

With `socket_comment_when: findings` (the default) nothing is posted when there is nothing to act on, and a comment from an earlier run collapses to a resolved note once its findings are gone. `dry_run: true` skips posting entirely.

It is a separate comment from both the security scan comment and the Socket App's, and duplicates neither: the App shows version transitions and score deltas for changed direct dependencies, this one shows action, severity, remediation and provenance.

### Turning it off

```yaml
with:
  run_socket: false               # the socket job (gate + report)
  socket_enable_firewall: false   # also unguards the twelve analysis installs
```

Note these are independent: `run_socket: false` removes the gate job and the comment but leaves the guarded installs in place.

## Branch protection

Require the aggregator checks `Frontend Analysis`, `Security` and `Socket` (plus the PR metadata checks from `pr-validation.yml`). Breaking-change enforcement remains inside the existing `Blocking Checks` status; it does not add a branch-protection check. These names are stable even when the underlying analysis steps change.

## Related

- [frontend-pr-analysis](./frontend-pr-analysis-workflow.md) — the frontend analysis pipeline this umbrella calls
- [pr-security-scan](./pr-security-scan-workflow.md) — the security pipeline this umbrella calls
- [pr-validation](./pr-validation.md) — the PR metadata validation this umbrella calls
- [go-pr-validation](./go-pr-validation.md) — the equivalent umbrella for Go repositories
