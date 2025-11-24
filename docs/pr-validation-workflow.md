# PR Validation Workflow

Comprehensive pull request validation workflow that enforces best practices, coding standards, and project conventions. Automatically checks PR title format, size, description quality, and ensures proper documentation.

## Features

- **Semantic PR titles** - Enforces conventional commits format
- **PR size tracking** - Automatic labeling (XS, S, M, L, XL)
- **Description quality** - Minimum length and required sections
- **Auto-labeling** - Based on changed files
- **Assignee checks** - Warns if no reviewer assigned
- **Issue linking** - Encourages linking to related issues
- **Changelog tracking** - Reminds to update CHANGELOG.md
- **Draft PR support** - Skips validations for draft PRs
- **Summary report** - Aggregated validation status

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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-validation.yml@main
```

### Custom Configuration

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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-validation.yml@main
    with:
      pr_title_types: |
        feat
        fix
        docs
        refactor
        test
        chore
      pr_title_scopes: |
        api
        cli
        auth
        config
      require_scope: true
      min_description_length: 100
      check_changelog: true
      enable_auto_labeler: true
    secrets:
      github_token: ${{ secrets.GITHUB_TOKEN }}
```

### With Custom Scopes

```yaml
jobs:
  validate:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-validation.yml@main
    with:
      pr_title_scopes: |
        auth
        ledger
        config
        client
        kubectl
        output
        cli
        deps
        ci
        release
      require_scope: false
```

## Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `runner_type` | string | `ubuntu-latest` | GitHub runner type |
| `pr_title_types` | string | (see below) | Allowed commit types (pipe-separated) |
| `pr_title_scopes` | string | `''` | Allowed scopes (pipe-separated, empty = any) |
| `require_scope` | boolean | `false` | Require scope in PR title |
| `min_description_length` | number | `50` | Minimum PR description length |
| `check_changelog` | boolean | `true` | Check if CHANGELOG.md is updated |
| `enable_auto_labeler` | boolean | `true` | Enable automatic labeling |
| `labeler_config_path` | string | `.github/labeler.yml` | Path to labeler config |

### Default PR Title Types

```
feat
fix
docs
style
refactor
perf
test
chore
ci
build
revert
```

## Secrets

### Optional

| Secret | Description |
|--------|-------------|
| `github_token` | GitHub token for API operations (labeling, commenting, etc.). Defaults to `GITHUB_TOKEN` if not provided. Required for all PR validation actions including posting comments, adding labels, and updating PR status. |

## Jobs

### skip-if-draft
Determines if PR is draft and sets flag to skip other jobs.

### pr-title
Validates PR title follows semantic commit format.

### pr-size
Calculates PR size and adds automatic size label (XS, S, M, L, XL).

### pr-description
Checks description length and recommended sections.

### pr-labels
Automatically adds labels based on changed files (requires labeler config).

### pr-assignee
Warns if no assignees are set on the PR.

### pr-linked-issues
Warns if PR doesn't link to any issues.

### pr-changelog
Checks if CHANGELOG.md was updated and comments if not.

### pr-checks-summary
Aggregates all check results into a summary report.

## PR Title Format

The workflow enforces semantic commit format:

```
<type>[optional scope]: <description>
```

**Examples:**
- `feat: add user authentication`
- `fix(api): resolve timeout issue`
- `docs: update installation guide`
- `refactor(cli): simplify command structure`

**Invalid:**
- `Add feature` (missing type)
- `feat: Add feature` (capital letter in description)
- `feat add feature` (missing colon)

## PR Size Labels

Automatically added based on lines changed:

| Lines Changed | Label |
|---------------|-------|
| < 50 | `size/XS` |
| 50-199 | `size/S` |
| 200-499 | `size/M` |
| 500-999 | `size/L` |
| ≥ 1000 | `size/XL` |

Large PRs (XL) receive a comment suggesting to break into smaller PRs.

## Auto-labeling

Requires a `.github/labeler.yml` configuration file in your repository:

```yaml
# Example labeler.yml
auth:
  - changed-files:
    - any-glob-to-any-file: 'internal/auth/**/*'
    - any-glob-to-any-file: 'pkg/auth/**/*'

api:
  - changed-files:
    - any-glob-to-any-file: 'api/**/*'

documentation:
  - changed-files:
    - any-glob-to-any-file: 'docs/**/*'
    - any-glob-to-any-file: '**/*.md'

tests:
  - changed-files:
    - any-glob-to-any-file: '**/*_test.go'
```

## Draft PR Behavior

When a PR is in draft mode:
- All validation checks are skipped
- No comments or labels are added
- Checks run automatically when PR is marked ready for review

## Changelog Checking

The workflow checks if `CHANGELOG.md` was updated. To skip the check:
- Add `skip-changelog` label
- Add `dependencies` label (auto-added by Dependabot)

## Required Sections

The workflow recommends including these sections in PR description:
- **Description** - What changes were made
- **Type of Change** - Feature, bug fix, etc.

## Linked Issues

Encourages linking PRs to issues using keywords:
- `Closes #123`
- `Fixes #456`
- `Resolves #789`
- `Relates to #101`

## Example Configurations

### Minimal (Defaults)

```yaml
jobs:
  validate:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-validation.yml@main
```

### Strict Validation

```yaml
jobs:
  validate:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-validation.yml@main
    with:
      require_scope: true
      min_description_length: 100
      check_changelog: true
```

### Without Auto-labeling

```yaml
jobs:
  validate:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-validation.yml@main
    with:
      enable_auto_labeler: false
```

### Custom Types Only

```yaml
jobs:
  validate:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-validation.yml@main
    with:
      pr_title_types: |
        feature
        bugfix
        hotfix
```

## Troubleshooting

### PR Title Validation Fails

**Issue**: PR title doesn't match expected format

**Solution**: Ensure title follows `type(scope): description` format:
- Type must be from allowed list
- Description must start with lowercase
- Colon and space are required

### Auto-labeling Not Working

**Issue**: Labels not added automatically

**Solution**:
1. Ensure `.github/labeler.yml` exists
2. Check file paths in labeler config match changed files
3. Verify `enable_auto_labeler` is `true`

### Changelog Check Too Strict

**Issue**: Always reminded to update CHANGELOG

**Solution**: Add `skip-changelog` label to PR or include `dependencies` in labels

### Size Label Not Updated

**Issue**: Size label doesn't reflect current PR size

**Solution**: Close and reopen PR, or make a new commit to trigger workflow

## Best Practices

1. Use semantic commit format consistently across all PRs
2. Keep PRs small (< 500 lines) for easier review
3. Always link PRs to related issues
4. Update CHANGELOG.md for user-facing changes
5. Add detailed PR descriptions (minimum 50 characters)
6. Assign reviewers before requesting review

## Related Workflows

- [Go CI](./go-ci-workflow.md) - Continuous integration testing
- [Go Security](./go-security-workflow.md) - Security scanning
- [PR Security Scan](./pr-security-scan-workflow.md) - Security scanning for PRs

---

**Last Updated:** 2025-11-22
**Version:** 1.0.0
