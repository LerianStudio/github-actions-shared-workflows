# Check Branch Workflow

Reusable workflow that enforces Git branching rules by validating that pull requests to `main` only come from allowed source branches (`develop`, `release-candidate`, or `hotfix/*`). When a violation is detected, it automatically posts a "Request Changes" review on the PR.

## Features

- **Source branch validation** - Blocks PRs to `main` from unauthorized branches
- **Automatic review** - Posts a REQUEST_CHANGES review explaining the violation
- **GPG-signed actions** - All bot actions are signed with GPG keys
- **GitHub App authentication** - Uses app token for secure API operations

## Usage

### Basic Usage

```yaml
name: "Enforce Branch PR's from Develop"

on:
  pull_request:
    branches:
      - main
    types:
      - opened
      - edited
      - synchronize
      - reopened

jobs:
  check-branch:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/check-branch.yml@main
    secrets:
      lerian_studio_push_bot_app_id: ${{ secrets.LERIAN_STUDIO_MIDAZ_PUSH_BOT_APP_ID }}
      lerian_studio_push_bot_private_key: ${{ secrets.LERIAN_STUDIO_MIDAZ_PUSH_BOT_PRIVATE_KEY }}
      lerian_ci_cd_user_gpg_key: ${{ secrets.LERIAN_CI_CD_USER_GPG_KEY }}
      lerian_ci_cd_user_gpg_key_password: ${{ secrets.LERIAN_CI_CD_USER_GPG_KEY_PASSWORD }}
      lerian_ci_cd_user_name: ${{ secrets.LERIAN_CI_CD_USER_NAME }}
      lerian_ci_cd_user_email: ${{ secrets.LERIAN_CI_CD_USER_EMAIL }}
```

## Secrets

All secrets are **required**.

| Secret | Description |
|--------|-------------|
| `lerian_studio_push_bot_app_id` | GitHub App ID for generating authentication tokens |
| `lerian_studio_push_bot_private_key` | GitHub App private key for authentication |
| `lerian_ci_cd_user_gpg_key` | GPG private key for signing bot actions |
| `lerian_ci_cd_user_gpg_key_password` | Passphrase for the GPG key |
| `lerian_ci_cd_user_name` | Git committer name for bot identity |
| `lerian_ci_cd_user_email` | Git committer email for bot identity |

## Allowed Branches

PRs targeting `main` are only allowed from:

| Branch Pattern | Example | Description |
|----------------|---------|-------------|
| `develop` | `develop` | Main development branch |
| `release-candidate` | `release-candidate` | Release candidate branch |
| `release-candidate/*` | `release-candidate/v1.2.0` | Versioned release candidate branches |
| `hotfix/*` | `hotfix/fix-critical-bug` | Hotfix branches |

Any PR from a branch not matching these patterns will be blocked with a REQUEST_CHANGES review.

## How It Works

1. **Authentication** - Generates a GitHub App token using the provided app credentials
2. **GPG Setup** - Imports GPG key for signed operations
3. **Branch Check** - Evaluates if the PR source branch matches allowed patterns
4. **Enforcement** - If the source branch is not allowed:
   - Posts a REQUEST_CHANGES review on the PR explaining the rule
   - Fails the workflow check, blocking the merge

## Behavior on Violation

When a PR is opened from a disallowed branch (e.g., `feat/my-feature` targeting `main`), the workflow:

1. Fails the status check
2. Posts a review comment:
   > Pull requests to **main** can only come from **develop**, **release-candidate**, or **hotfix** branches. Please **change base**!!!

The developer should either:
- Change the PR base to `develop` instead of `main`
- Create a proper `release-candidate` or `hotfix/*` branch

## Troubleshooting

### Workflow Not Triggering

**Issue**: PRs to `main` don't trigger the check

**Solution**: Ensure the caller workflow has the correct trigger configuration:
```yaml
on:
  pull_request:
    branches:
      - main
    types:
      - opened
      - edited
      - synchronize
      - reopened
```

### Review Not Posted

**Issue**: Workflow fails but no review appears on the PR

**Solution**:
1. Verify the GitHub App has permission to post reviews
2. Check that `lerian_studio_push_bot_app_id` and `lerian_studio_push_bot_private_key` are correctly configured
3. Ensure the App is installed on the repository

### False Positives

**Issue**: Legitimate branch blocked

**Solution**: Verify the branch name matches one of the allowed patterns exactly:
- `develop` (exact match)
- `release-candidate` (exact match)
- `release-candidate/...` (prefix match)
- `hotfix/...` (prefix match)

## Related Workflows

- [PR Validation](./pr-validation-workflow.md) - Comprehensive PR validation (includes optional source branch checking)
- [Build](./build-workflow.md) - Build and test workflow

---

**Last Updated:** 2026-02-25
**Version:** 1.0.0
