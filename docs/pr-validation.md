<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>pr-validation</h1></td>
  </tr>
</table>

Comprehensive pull request validation workflow that enforces best practices, coding standards, project conventions, and explicit PR author acknowledgement of breaking changes.

## Features

- **Semantic PR titles** — Enforces conventional commits format
- **PR size tracking** — Automatic labeling (XS, S, M, L, XL)
- **Description quality** — Minimum length and required sections
- **Auto-labeling** — Based on changed files
- **Auto-assign** — Assigns PR author when no assignee is set (skips bots)
- **Draft PR support** — Runs and enforces the mandatory guard (and still writes the step summary) while deferring title, branch, description, advisory, PR comments, reporter output, guard comments, and Slack notifications until ready for review
- **Source branch validation** — Enforce PRs to protected branches come from specific source branches
- **Mandatory breaking change guard** — Detects breaking-change commits on every target branch and blocks breaking changes without PR author acknowledgement
- **Commit signature validation** — Blocks the PR when any of its commits is unsigned or unverified, listing every offending commit
- **Dry run mode** — Preview validations without posting comments or labels
- **Summary report** — Aggregated validation status (step summary + idempotent PR comment)
- **Idempotent feedback** — Source branch failures and the mergeability summary are upserted via stable markers (no stacked duplicates across commits)

## Architecture

Accepts original `pull_request` events only. It uses a mandatory fail-closed guard followed by a **2-tier fail-fast model** to minimize runner cost and provide fast feedback:

```
pr-validation.yml (reusable workflow)

  breaking-change-guard (validates the event and always detects, including drafts)
    └── src/validate/breaking-change-guard@v1 (exact visible-line acknowledgement)
               ↓
  Tier 1 — blocking-checks (always enforces the guard; no checkout, ~5s)
    ├── breaking-change enforcement     (also runs for drafts)
    ├── src/validate/pr-source-branch   (non-draft source branch check)
    ├── src/validate/pr-title           (non-draft semantic title check)
    ├── src/validate/pr-description     (non-draft description quality)
    └── src/validate/pr-commit-signatures (non-draft commit signature check)
              ↓ (only continues if all pass)
  Tier 2 — advisory-checks (shared checkout)
    ├── src/validate/pr-metadata        (assignee + linked issues)
    ├── src/validate/pr-size            (size calculation + labeling)
    └── src/validate/pr-labels          (auto-label by files)
              ↓
  Summary — pr-checks-summary (always runs, step summary)
              ↓
  Reports — breaking-change comment + pr-validation-reporter
              ↓
  Notify  — slack-notify.yml (optional)
```

Breaking-change enforcement reuses the existing `Blocking Checks` job. Callers do not need a new branch-protection check.

## Usage

### Basic Usage

The caller must use the `pull_request` event. `pull_request_target`, `workflow_dispatch`, and calls without complete pull request event data fail closed. Do not add a target-branch filter to the trigger: the mandatory guard applies to every PR target branch.

The `edited` trigger is mandatory because PR body changes can add or remove the acknowledgement. Keep `ready_for_review` so a draft-to-ready transition runs the deferred validations.

```yaml
name: PR Validation

on:
  pull_request:
    types: [opened, synchronize, reopened, edited, ready_for_review]

permissions:
  contents: read
  pull-requests: write
  issues: write

jobs:
  validate:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-validation.yml@tier-1
    secrets: inherit
```

### Custom Configuration

```yaml
jobs:
  validate:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-validation.yml@tier-1
    with:
      pr_title_types: |
        feat
        fix
        docs
        refactor
        test
        chore
      require_scope: true
      enable_auto_labeler: true
    secrets: inherit
```

### With Source Branch Validation

```yaml
jobs:
  validate:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-validation.yml@tier-1
    with:
      enforce_source_branches: true
      allowed_source_branches: 'develop|release-candidate|hotfix/*'
    secrets: inherit
```

### Without Slack (repositories with no `SLACK_WEBHOOK_URL`)

```yaml
jobs:
  validate:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-validation.yml@tier-1
    with:
      enable_slack_notification: false
    secrets: inherit
```

Omitting the secret is not enough on its own: the `notify` job still runs, consumes a
runner and shows up as `validate / Notify / Send Notification` in the PR check list, only
to skip internally. Setting `enable_slack_notification: false` skips the job outright, so
the inert check disappears. `dry_run: true` also disables it, but takes comments and labels
down with it — use this input when Slack is the only thing you want off.

The same input exists on `go-pr-validation.yml`, `js-pr-validation.yml`,
`pr-security-scan.yml`, `go-pr-analysis.yml` and `frontend-pr-analysis.yml`, with the same
name and the same `true` default.

### Dry Run (preview without side effects)

```yaml
jobs:
  validate:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-validation.yml@tier-1
    with:
      dry_run: true
    secrets: inherit
```

## Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `runner_type` | string | `blacksmith-4vcpu-ubuntu-2404` | GitHub runner type |
| `pr_checks_summary_runner_type` | string | `''` | Optional runner override for the PR Checks Summary job only; empty falls back to `vars.GENERAL_RUNNERS`, then `runner_type` |
| `dry_run` | boolean | `false` | Preview validations without posting comments or labels |
| `pr_title_types` | string | (see below) | Allowed commit types (newline-separated) |
| `pr_title_scopes` | string | `''` | Allowed scopes (newline-separated, empty = any) |
| `require_scope` | boolean | `false` | Require scope in PR title |
| `enable_auto_labeler` | boolean | `true` | Enable automatic labeling |
| `enable_slack_notification` | boolean | `true` | Send the validation verdict to Slack. Set to `false` in repositories without `SLACK_WEBHOOK_URL` so the job is skipped entirely instead of running just to skip internally |
| `labeler_config_path` | string | `.github/labeler.yml` | Path to labeler config |
| `enforce_source_branches` | boolean | `true` | Enforce source branch rules. Auto-skips when the target is neither in `target_branches_for_source_check` nor named in `source_branch_rules` |
| `allowed_source_branches` | string | `develop\|release-candidate\|hotfix/*` | Allowed source branches (pipe-separated, supports `*` wildcard) |
| `target_branches_for_source_check` | string | `main` | Target branches that require source branch validation |
| `source_branch_rules` | string | `''` | Per-target source rules as JSON. A target listed here uses its own patterns and ignores the two inputs above |
| `require_verified_commits` | boolean | `true` | Block the PR when any of its commits is unsigned or has an unverified signature |

The breaking change guard has no enable input, target-branch input, acknowledgement input, or opt-out. It applies to every caller and every PR target branch. `dry_run: true` remains a global preview mode without guard enforcement; it is not a guard-specific opt-out and does not change normal `dry_run: false` operation. Existing callers must migrate their `pull_request.types` list to include both `edited` and `ready_for_review`; otherwise body edits and draft-to-ready transitions do not rerun validation.

## Outputs

| Output | Values | Description |
|--------|--------|-------------|
| `has_breaking_changes` | `true` / `false` | Whether the PR contains at least one breaking-change commit |
| `breaking_change_approved` | `true` / `false` | Compatibility field name: whether the PR description contains the exact author acknowledgement. It records intentional awareness and does not grant maintainer permission. |
| `breaking_change_result` | `success` / `failure` | Normalized guard result used by `Blocking Checks`, reports, and notifications |

Outputs are closed by default. Missing, skipped, or cancelled guard state returns `has_breaking_changes: false`, `breaking_change_approved: false`, and `breaking_change_result: failure`. The `breaking_change_approved` name is retained only as a compatibility contract. Consumers must interpret `true` as author acknowledgement, not maintainer permission.

## Breaking Change Author Acknowledgement

When a PR contains a breaking-change commit, its description must contain this exact, case-sensitive, standalone visible line:

```text
Breaking change acknowledged: I understand that this PR intentionally introduces a breaking change and requires the next release to be a major version.
```

Partial text, case changes, similar wording, hidden content, blockquotes, and fenced code do not acknowledge the breaking change. The line must be visible as its own line in the rendered PR description. Any PR author can supply it. The line proves intentional awareness of the breaking change and expected major release; it does not represent maintainer permission. A breaking change with the exact visible line passes. A breaking change without it fails. A PR without breaking changes passes.

The guard is mandatory on every target branch. There is no opt-out. The action stays on the released `@v1` line; the acknowledgement describes release intent but does not classify or select a release version.

### Feedback comments

For every non-draft live run, including detector failure or cancellation, the workflow uses `github.token` to manage one best-effort comment owned only when the author is exactly `github-actions[bot]` and the body starts with the exact marker line:

- A breaking change creates or updates the comment with `Author acknowledged` or `Awaiting author acknowledgement` state and the exact acknowledgement.
- Detection or guard-job failure replaces stale acknowledgement with one `Detection failed` comment and deletes duplicate owned comments.
- Duplicate owned marker comments are deleted.
- When breaking changes disappear, all owned guard comments are deleted.
- Before any comment mutation, the workflow fetches the current PR and stops if its current head SHA differs from the event head SHA.
- Fork token write restrictions and comment API failures never affect enforcement. The workflow never falls back to another bot identity.

### Default PR Title Types

```
feat fix docs style refactor perf test chore ci build revert
```

## Secrets

| Secret | Required | Description |
|--------|----------|-------------|
| `MANAGE_TOKEN` | No | GitHub token with elevated permissions for labeling, commenting, and reviews. Falls back to `github.token`. |
| `SLACK_WEBHOOK_URL` | No | Slack webhook URL for notifications. Skipped if not provided. |

## Jobs

| Job | Tier | Composites | Condition |
|-----|------|------------|-----------|
| `breaking-change-guard` | mandatory detection | `breaking-change-guard@v1` | always, including drafts |
| `blocking-checks` | 1 (fail-fast) | guard enforcement, `pr-source-branch`, `pr-title`, `pr-description`, `pr-commit-signatures` | always; drafts run guard enforcement only |
| `advisory-checks` | 2 (informational) | `pr-metadata`, `pr-size`, `pr-labels` | non-draft, blocking-checks passed |
| `pr-checks-summary` | — | `pr-checks-summary` | always (writes to step summary) |
| `breaking-change-comment` | — | `actions/github-script` | every non-draft live run, including detector failure or cancellation |
| `pr-validation-report` | — | `pr-validation-reporter` | non-draft (upserts single PR comment) |
| `notify` | — | `slack-notify.yml` | non-draft, `!dry_run` |

### Blocking checks (Tier 1)
- Run without checkout (lightweight, ~5 seconds)
- Always enforce both the guard job state and its normalized output, including on drafts
- Skip existing source branch, title, description, commit signature, and collector steps on drafts; their non-draft behavior is unchanged
- On non-drafts, every validation runs even if one fails (`continue-on-error` per step)
- Job fails if the guard job, normalized guard output, or **any** existing blocking check fails, preventing advisory checks from running
- In dry-run mode, guard state is logged but does not fail `Blocking Checks`

### Fail-closed detection

An event-validation step rejects any original event other than `pull_request` and rejects missing PR number, head ref/SHA, or base ref/SHA data. Therefore `pull_request_target`, `workflow_dispatch`, and incomplete PR events fail closed.

The event validation, detector checkout, and released guard action tolerate step errors only so a final `always()` normalization step can emit deterministic outputs. Event validation failure, checkout failure, action failure, cancellation, skipped execution, or missing/malformed action outputs normalize to:

- `breaking_change_result: failure`
- `has_breaking_changes: false`
- `breaking_change_approved: false`

The detection job can remain successful when normalization handles the fault. Live enforcement still fails through `Blocking Checks`, which requires both the detector job result and normalized output to be `success`. If the detector job itself is cancelled or cannot emit outputs, enforcement fails closed.

Summary and reporter inputs normalize the combined detector job and output state: only two `success` values produce guard success. They also receive the independent `Blocking Checks` job result. Slack treats every `Blocking Checks` state other than `success` as failure and reports it as `Blocking Checks`, not as a guard failure.

### Commit signature validation

Enabled by default (`require_verified_commits: true`) and enforced through the existing `Blocking Checks` job — no new branch-protection check is needed.

The check reads GitHub's own verification verdict (`commit.verification.verified`) for **every** commit in the PR, not only `HEAD`, and uses `github.paginate` so PRs with more than 100 commits are fully evaluated. Every offending commit is reported at once — in the job summary as a table (short SHA + link, author, verification reason) and as `::error::` annotations — so a single run surfaces all findings instead of the first one.

| Situation | Result |
|-----------|--------|
| Every commit verified | ✅ `Blocking Checks` passes |
| One or more commits unsigned/unverified | ❌ `Blocking Checks` fails, merge blocked |
| PR declares more commits than the API returns (250-commit cap) | ❌ fails closed — split the PR so all commits can be validated |
| `require_verified_commits: false` | Step skipped, no row in summary or report |
| `dry_run: true` | Findings reported, `Blocking Checks` not failed |

Remediation (also printed in the job summary, with `<base-branch>` already resolved to the pull request's own base branch):

```bash
git config --local commit.gpgsign true
git rebase --exec 'git commit --amend --no-edit -S' origin/<base-branch>
git push --force-with-lease
```

The step runs with read-only permissions and emits no commit metadata beyond what is already visible in the repository. See [`pr-commit-signatures`](../src/validate/pr-commit-signatures/README.md).

### Advisory checks (Tier 2)
- Share a single `checkout` with `fetch-depth: 0`
- Only run if all blocking checks passed
- Never block merge — informational only

## Dry Run Behavior

When `dry_run: true`:
- Breaking-change detection still runs and emits deterministic outputs
- The guard prints all resolved values but does not fail `Blocking Checks`
- The breaking-change comment and validation report comments are not posted
- Title, description, commit signature, and metadata validations still run (read-only checks)
- Unsigned/unverified commits are reported but do not fail `Blocking Checks`
- Size is calculated and logged but **labels are not applied**
- Source branch is validated but **the failure comment is not posted/updated**
- Auto-labeling is **skipped entirely**
- Slack notification is **skipped**
- Summary report includes a DRY RUN banner

## Draft PR Behavior

When a PR is in draft mode, mandatory breaking-change detection and guard enforcement still run. `Blocking Checks` is the existing required check, so a breaking change without author acknowledgement or a detector failure blocks the draft without adding a new required check. Existing source branch, title, description, commit signature, and collector steps remain skipped, and the step summary is still written. Advisory checks, PR comments, reporter output, guard comments, and Slack also remain skipped until the PR is marked ready for review.

Every caller must include `ready_for_review` so deferred validation runs on that transition. Every caller must include `edited` so adding, changing, or removing the acknowledgement in the PR body reruns enforcement.

## PR Size Labels

| Lines Changed | Label |
|---------------|-------|
| < 50 | `size/XS` |
| 50–199 | `size/S` |
| 200–499 | `size/M` |
| 500–999 | `size/L` |
| >= 1000 | `size/XL` |

## PR Title Format

```
<type>[optional scope]: <description>
```

- `feat: add user authentication`
- `fix(api): resolve timeout issue`
- `docs: update installation guide`

## Related Workflows

- [Go CI](./go-ci-workflow.md) — Continuous integration testing
- [Go Security](./go-security-workflow.md) — Security scanning
- [PR Security Scan](./pr-security-scan-workflow.md) — Security scanning for PRs

---

**Last Updated:** 2026-08-06
**Release line:** `v1`

## Per-target source rules

`allowed_source_branches` and `target_branches_for_source_check` describe a single rule applied to every protected branch. When protected branches accept different sources, use `source_branch_rules` instead:

```yaml
with:
  enforce_source_branches: true
  source_branch_rules: |
    {
      "main": "release-candidate|hotfix/*",
      "release-candidate": "develop-*|hotfix/*"
    }
```

| Target | Source | Result |
|---|---|---|
| `release-candidate` | `develop-midaz` | allowed |
| `release-candidate` | `hotfix/CVE-123` | allowed |
| `release-candidate` | `develop` | **blocked** |
| `main` | `release-candidate` | allowed |
| `main` | `develop` | **blocked** — promoted through the release candidate, never merged directly |
| `develop` | anything | not validated — no rule, not a listed target |

A target present in `source_branch_rules` overrides **both** flat inputs: it uses its own patterns instead of `allowed_source_branches`, and it is validated even when `target_branches_for_source_check` does not list it. Targets absent from the map keep following the two flat inputs, so leaving `source_branch_rules` empty preserves the current behavior exactly.
