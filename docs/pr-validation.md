<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>pr-validation</h1></td>
  </tr>
</table>

Comprehensive pull request validation workflow that enforces best practices, coding standards, and project conventions. Automatically checks PR title format, size, description quality, and ensures proper documentation.

## Features

- **Semantic PR titles** — Enforces conventional commits format
- **PR size tracking** — Automatic labeling (XS, S, M, L, XL)
- **Description quality** — Minimum length and required sections
- **Auto-labeling** — Based on changed files
- **Metadata checks** — Warns if no assignee or linked issues
- **Changelog tracking** — Reminds to update CHANGELOG.md
- **Draft PR support** — Skips validations for draft PRs
- **Source branch validation** — Enforce PRs to protected branches come from specific source branches
- **Dry run mode** — Preview validations without posting comments or labels
- **Summary report** — Aggregated validation status

## Architecture

```
pr-validation.yml (reusable workflow)
    ├── src/validate/pr-source-branch   (source branch check)
    ├── src/validate/pr-title           (semantic title check)
    ├── src/validate/pr-size            (size calculation + labeling)
    ├── src/validate/pr-description     (description quality)
    ├── src/validate/pr-labels          (auto-label by files)
    ├── src/validate/pr-metadata        (assignee + linked issues)
    ├── src/validate/pr-changelog       (changelog check)
    └── slack-notify.yml                (optional notification)
```

## Usage

### Basic Usage

```yaml
name: PR Validation

on:
  pull_request:
    branches: [develop, release-candidate, main]
    types: [opened, synchronize, reopened, ready_for_review]

permissions:
  contents: read
  pull-requests: write
  issues: write

jobs:
  validate:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-validation.yml@v1.x.x
    secrets: inherit
```

### Custom Configuration

```yaml
jobs:
  validate:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-validation.yml@v1.x.x
    with:
      pr_title_types: |
        feat
        fix
        docs
        refactor
        test
        chore
      require_scope: true
      min_description_length: 100
      check_changelog: true
      enable_auto_labeler: true
    secrets: inherit
```

### With Source Branch Validation

```yaml
jobs:
  validate:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-validation.yml@v1.x.x
    with:
      enforce_source_branches: true
      allowed_source_branches: 'develop|release-candidate|hotfix/*'
      target_branches_for_source_check: 'main'
    secrets: inherit
```

### Dry Run (preview without side effects)

```yaml
jobs:
  validate:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-validation.yml@v1.x.x
    with:
      dry_run: true
    secrets: inherit
```

## Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `runner_type` | string | `blacksmith-4vcpu-ubuntu-2404` | GitHub runner type |
| `dry_run` | boolean | `false` | Preview validations without posting comments or labels |
| `pr_title_types` | string | (see below) | Allowed commit types (newline-separated) |
| `pr_title_scopes` | string | `''` | Allowed scopes (newline-separated, empty = any) |
| `require_scope` | boolean | `false` | Require scope in PR title |
| `min_description_length` | number | `50` | Minimum PR description length |
| `check_changelog` | boolean | `true` | Check if CHANGELOG.md is updated |
| `enable_auto_labeler` | boolean | `true` | Enable automatic labeling |
| `labeler_config_path` | string | `.github/labeler.yml` | Path to labeler config |
| `enforce_source_branches` | boolean | `false` | Enforce source branch rules |
| `allowed_source_branches` | string | `develop\|release-candidate\|hotfix/*` | Allowed source branches (pipe-separated, supports `*` wildcard) |
| `target_branches_for_source_check` | string | `main` | Target branches that require source branch validation |

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

| Job | Condition | Composite |
|-----|-----------|-----------|
| `pr-source-branch` | `enforce_source_branches` | `src/validate/pr-source-branch` |
| `pr-title` | always (non-draft) | `src/validate/pr-title` |
| `pr-size` | always (non-draft) | `src/validate/pr-size` |
| `pr-description` | always (non-draft) | `src/validate/pr-description` |
| `pr-labels` | `enable_auto_labeler && !dry_run` | `src/validate/pr-labels` |
| `pr-metadata` | always (non-draft) | `src/validate/pr-metadata` |
| `pr-changelog` | `check_changelog` | `src/validate/pr-changelog` |
| `pr-checks-summary` | always | inline |
| `notify` | `!dry_run` | `slack-notify.yml` |

## Dry Run Behavior

When `dry_run: true`:
- Title, description, and metadata validations still run (read-only checks)
- Size is calculated and logged but **labels are not applied**
- Changelog is checked but **comments are not posted**
- Source branch is validated but **REQUEST_CHANGES review is not posted**
- Auto-labeling is **skipped entirely**
- Slack notification is **skipped**
- Summary report includes a DRY RUN banner

## Draft PR Behavior

When a PR is in draft mode, all validation jobs are skipped. Checks run automatically when the PR is marked ready for review.

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

## Changelog Checking

To skip the changelog check, add one of these labels:
- `skip-changelog`
- `dependencies` (auto-added by Dependabot)

## Related Workflows

- [Go CI](./go-ci.md) — Continuous integration testing
- [Go Security](./go-security.md) — Security scanning
- [PR Security Scan](./pr-security-scan.md) — Security scanning for PRs

---

**Last Updated:** 2026-03-24
**Version:** 2.0.0
