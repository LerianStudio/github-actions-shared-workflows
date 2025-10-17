# Release Workflow

Reusable workflow for semantic versioning and automated release management. Creates releases based on conventional commits and manages version tags with GPG signing.

## Features

- **Semantic versioning**: Automatic version calculation from conventional commits
- **GPG signing**: Signed commits and tags for security
- **GitHub App authentication**: Higher rate limits and better security
- **Hotfix support**: Separate configuration for hotfix branches
- **Backmerge support**: Automatic backmerging of releases
- **Conventional commits**: Enforces commit message standards

## Usage

### Basic Example

```yaml
name: Release Pipeline
on:
  push:
    branches:
      - develop
      - release-candidate
      - main

jobs:
  release:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/release.yml@main
    secrets:
      lerian_studio_push_bot_app_id: ${{ secrets.LERIAN_STUDIO_MIDAZ_PUSH_BOT_APP_ID }}
      lerian_studio_push_bot_private_key: ${{ secrets.LERIAN_STUDIO_MIDAZ_PUSH_BOT_PRIVATE_KEY }}
      lerian_ci_cd_user_gpg_key: ${{ secrets.LERIAN_CI_CD_USER_GPG_KEY }}
      lerian_ci_cd_user_gpg_key_password: ${{ secrets.LERIAN_CI_CD_USER_GPG_KEY_PASSWORD }}
      lerian_ci_cd_user_name: ${{ secrets.LERIAN_CI_CD_USER_NAME }}
      lerian_ci_cd_user_email: ${{ secrets.LERIAN_CI_CD_USER_EMAIL }}
```

### With Custom Runner

```yaml
release:
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/release.yml@main
  with:
    runner: "firmino-lxc-runners"
    semantic_version: "23.0.8"
  secrets:
    lerian_studio_push_bot_app_id: ${{ secrets.LERIAN_STUDIO_MIDAZ_PUSH_BOT_APP_ID }}
    lerian_studio_push_bot_private_key: ${{ secrets.LERIAN_STUDIO_MIDAZ_PUSH_BOT_PRIVATE_KEY }}
    lerian_ci_cd_user_gpg_key: ${{ secrets.LERIAN_CI_CD_USER_GPG_KEY }}
    lerian_ci_cd_user_gpg_key_password: ${{ secrets.LERIAN_CI_CD_USER_GPG_KEY_PASSWORD }}
    lerian_ci_cd_user_name: ${{ secrets.LERIAN_CI_CD_USER_NAME }}
    lerian_ci_cd_user_email: ${{ secrets.LERIAN_CI_CD_USER_EMAIL }}
```

### Complete Release Pipeline

```yaml
name: Release Pipeline
on:
  push:
    branches:
      - develop
      - release-candidate
      - main
    paths-ignore:
      - '**/*.md'
      - '**/*.txt'
      - '**/*.env'

permissions:
  id-token: write
  contents: write
  pull-requests: write

jobs:
  tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: make test

  release:
    needs: tests
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/release.yml@main
    secrets:
      lerian_studio_push_bot_app_id: ${{ secrets.LERIAN_STUDIO_MIDAZ_PUSH_BOT_APP_ID }}
      lerian_studio_push_bot_private_key: ${{ secrets.LERIAN_STUDIO_MIDAZ_PUSH_BOT_PRIVATE_KEY }}
      lerian_ci_cd_user_gpg_key: ${{ secrets.LERIAN_CI_CD_USER_GPG_KEY }}
      lerian_ci_cd_user_gpg_key_password: ${{ secrets.LERIAN_CI_CD_USER_GPG_KEY_PASSWORD }}
      lerian_ci_cd_user_name: ${{ secrets.LERIAN_CI_CD_USER_NAME }}
      lerian_ci_cd_user_email: ${{ secrets.LERIAN_CI_CD_USER_EMAIL }}
```

## Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `semantic_version` | string | `23.0.8` | Semantic release version to use |
| `runner` | string | `ubuntu-24.04` | GitHub runner type |

## Secrets

### Required Secrets

| Secret | Description |
|--------|-------------|
| `lerian_studio_push_bot_app_id` | GitHub App ID for authentication |
| `lerian_studio_push_bot_private_key` | GitHub App private key |
| `lerian_ci_cd_user_gpg_key` | GPG private key for signing commits |
| `lerian_ci_cd_user_gpg_key_password` | GPG key passphrase |
| `lerian_ci_cd_user_name` | Git committer name |
| `lerian_ci_cd_user_email` | Git committer email |

## Outputs

| Output | Description |
|--------|-------------|
| `gpg_fingerprint` | GPG key fingerprint used for signing |

## Branch Strategy

### develop → Beta Releases

Commits to `develop` branch create beta releases:
- Version: `v1.2.3-beta.1`
- Pre-release: Yes
- Use case: Development testing

### release-candidate → RC Releases

Commits to `release-candidate` branch create RC releases:
- Version: `v1.2.3-rc.1`
- Pre-release: Yes
- Use case: Staging/UAT testing

### main → Production Releases

Commits to `main` branch create production releases:
- Version: `v1.2.3`
- Pre-release: No
- Use case: Production deployment

### hotfix/* → Hotfix Releases

Commits to `hotfix/*` branches use `.releaserc.hotfix` configuration:
- Version: `v1.2.4` (patch bump)
- Pre-release: No
- Use case: Emergency fixes

## Conventional Commits

The workflow uses conventional commits to determine version bumps:

### Breaking Changes (Major)

```
feat!: remove deprecated API endpoint

BREAKING CHANGE: The /api/v1/old endpoint has been removed
```

Version: `1.0.0` → `2.0.0`

### Features (Minor)

```
feat: add user authentication
```

Version: `1.0.0` → `1.1.0`

### Fixes (Patch)

```
fix: resolve memory leak in transaction processor
```

Version: `1.0.0` → `1.0.1`

### Other Types (No Version Bump)

```
docs: update API documentation
chore: update dependencies
style: fix code formatting
refactor: simplify authentication logic
perf: optimize database queries
test: add unit tests for auth module
ci: update GitHub Actions workflow
```

No version bump, but included in changelog.

## Configuration Files

### .releaserc (Default)

Used for `develop`, `release-candidate`, and `main` branches:

```json
{
  "branches": [
    "main",
    {
      "name": "release-candidate",
      "prerelease": "rc"
    },
    {
      "name": "develop",
      "prerelease": "beta"
    }
  ],
  "plugins": [
    "@semantic-release/commit-analyzer",
    "@semantic-release/release-notes-generator",
    "@semantic-release/github"
  ]
}
```

### .releaserc.hotfix (Hotfix)

Used for `hotfix/*` branches:

```json
{
  "branches": [
    {
      "name": "hotfix/*",
      "prerelease": false
    }
  ],
  "plugins": [
    "@semantic-release/commit-analyzer",
    "@semantic-release/release-notes-generator",
    "@semantic-release/github"
  ]
}
```

## Workflow Steps

1. **Create GitHub App Token**: Generate authentication token with higher rate limits
2. **Checkout Repository**: Clone with full history for versioning
3. **Sync with Remote**: Ensure latest changes are pulled
4. **Import GPG Key**: Import and configure GPG key for signing
5. **Initialize package.json**: Create if doesn't exist
6. **Install Plugins**: Install semantic-release plugins
7. **Select Configuration**: Choose `.releaserc` or `.releaserc.hotfix`
8. **Run Semantic Release**: Calculate version and create release

## GPG Signing

### Why GPG Signing?

- **Authenticity**: Verify commits are from authorized sources
- **Integrity**: Ensure commits haven't been tampered with
- **Compliance**: Meet security requirements for production releases

### Setup GPG Key

1. **Generate GPG key**:
```bash
gpg --full-generate-key
```

2. **Export private key**:
```bash
gpg --armor --export-secret-keys YOUR_EMAIL > private-key.asc
```

3. **Add to GitHub Secrets**:
- `LERIAN_CI_CD_USER_GPG_KEY`: Contents of `private-key.asc`
- `LERIAN_CI_CD_USER_GPG_KEY_PASSWORD`: Key passphrase

4. **Add public key to GitHub**:
```bash
gpg --armor --export YOUR_EMAIL
```
Add to GitHub Settings → SSH and GPG keys

## GitHub App Setup

### Why GitHub App?

- **Higher rate limits**: 5,000 requests/hour vs 1,000 for PAT
- **Better security**: Scoped permissions, automatic token expiration
- **Audit trail**: Better tracking of automated actions

### Create GitHub App

1. Go to GitHub Settings → Developer settings → GitHub Apps
2. Click "New GitHub App"
3. Configure:
   - **Name**: `Lerian CI/CD Bot`
   - **Homepage URL**: Your organization URL
   - **Permissions**:
     - Contents: Read & Write
     - Pull Requests: Read & Write
     - Metadata: Read-only
4. Generate private key
5. Install app to repositories
6. Add to secrets:
   - `LERIAN_STUDIO_MIDAZ_PUSH_BOT_APP_ID`: App ID
   - `LERIAN_STUDIO_MIDAZ_PUSH_BOT_PRIVATE_KEY`: Private key contents

## Best Practices

### 1. Use Conventional Commits

Enforce with commitlint:

```yaml
# .commitlintrc.yml
extends:
  - '@commitlint/config-conventional'
rules:
  type-enum:
    - 2
    - always
    - [feat, fix, docs, style, refactor, perf, test, chore, revert, ci, build]
```

### 2. Protect Release Branches

Configure branch protection:
- Require pull request reviews
- Require status checks to pass
- Require signed commits
- Include administrators

### 3. Use Environment Protection

```yaml
jobs:
  release:
    environment:
      name: production
```

Add required reviewers for production releases.

### 4. Ignore Non-code Changes

```yaml
on:
  push:
    paths-ignore:
      - '**/*.md'
      - '**/*.txt'
      - '**/*.env'
```

### 5. Run Tests Before Release

```yaml
jobs:
  tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run tests
        run: make test

  release:
    needs: tests
```

## Troubleshooting

### Release Not Created

**Issue**: Workflow runs but no release is created

**Solutions**:
1. Check commit messages follow conventional commits
2. Verify branch is configured in `.releaserc`
3. Check if version already exists
4. Review semantic-release logs

### GPG Signing Failed

**Issue**: Cannot sign commits with GPG key

**Solutions**:
1. Verify GPG key is valid: `gpg --list-secret-keys`
2. Check passphrase is correct
3. Ensure key hasn't expired
4. Verify key format (ASCII armored)

### Authentication Failed

**Issue**: Cannot push tags or create releases

**Solutions**:
1. Verify GitHub App is installed on repository
2. Check App permissions (Contents: Write)
3. Verify App ID and private key are correct
4. Ensure App token hasn't expired

### Wrong Version Calculated

**Issue**: Semantic release calculates incorrect version

**Solutions**:
1. Check commit message format
2. Verify branch configuration in `.releaserc`
3. Review previous tags: `git tag -l`
4. Check for BREAKING CHANGE in commit body

### Hotfix Configuration Not Used

**Issue**: Hotfix branch uses wrong configuration

**Solutions**:
1. Verify branch name matches `hotfix/*` pattern
2. Check `.releaserc.hotfix` exists
3. Review workflow step logs

## Examples

### Basic Release Workflow

```yaml
name: Release
on:
  push:
    branches: [main, develop, release-candidate]

jobs:
  release:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/release.yml@main
    secrets:
      lerian_studio_push_bot_app_id: ${{ secrets.APP_ID }}
      lerian_studio_push_bot_private_key: ${{ secrets.APP_PRIVATE_KEY }}
      lerian_ci_cd_user_gpg_key: ${{ secrets.GPG_KEY }}
      lerian_ci_cd_user_gpg_key_password: ${{ secrets.GPG_PASSWORD }}
      lerian_ci_cd_user_name: ${{ secrets.USER_NAME }}
      lerian_ci_cd_user_email: ${{ secrets.USER_EMAIL }}
```

### Release with Build Pipeline

```yaml
name: Release Pipeline
on:
  push:
    branches: [main, develop, release-candidate]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: make test

  release:
    needs: test
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/release.yml@main
    secrets:
      lerian_studio_push_bot_app_id: ${{ secrets.APP_ID }}
      lerian_studio_push_bot_private_key: ${{ secrets.APP_PRIVATE_KEY }}
      lerian_ci_cd_user_gpg_key: ${{ secrets.GPG_KEY }}
      lerian_ci_cd_user_gpg_key_password: ${{ secrets.GPG_PASSWORD }}
      lerian_ci_cd_user_name: ${{ secrets.USER_NAME }}
      lerian_ci_cd_user_email: ${{ secrets.USER_EMAIL }}

  build:
    needs: release
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build and push
        run: make build-push
```

### Hotfix Workflow

```yaml
name: Hotfix Release
on:
  push:
    branches:
      - 'hotfix/**'

jobs:
  release:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/release.yml@main
    secrets:
      lerian_studio_push_bot_app_id: ${{ secrets.APP_ID }}
      lerian_studio_push_bot_private_key: ${{ secrets.APP_PRIVATE_KEY }}
      lerian_ci_cd_user_gpg_key: ${{ secrets.GPG_KEY }}
      lerian_ci_cd_user_gpg_key_password: ${{ secrets.GPG_PASSWORD }}
      lerian_ci_cd_user_name: ${{ secrets.USER_NAME }}
      lerian_ci_cd_user_email: ${{ secrets.USER_EMAIL }}
```

## Semantic Release Plugins

### Included Plugins

- **@semantic-release/commit-analyzer**: Analyzes commits to determine version bump
- **@semantic-release/release-notes-generator**: Generates release notes from commits
- **@semantic-release/github**: Creates GitHub releases
- **@semantic-release/exec**: Executes custom scripts (installed automatically)
- **conventional-changelog-conventionalcommits**: Conventional commits support
- **@saithodev/semantic-release-backmerge**: Automatic backmerging

### Custom Plugins

Add custom plugins in `.releaserc`:

```json
{
  "plugins": [
    "@semantic-release/commit-analyzer",
    "@semantic-release/release-notes-generator",
    "@semantic-release/changelog",
    "@semantic-release/npm",
    "@semantic-release/github",
    "@semantic-release/git"
  ]
}
```

## Related Workflows

- [GitOps Update](gitops-update-workflow.md) - Update deployments after release
- [PR Security Scan](pr-security-scan-workflow.md) - Security checks before release
- [API Dog E2E Tests](api-dog-e2e-tests-workflow.md) - E2E tests after release
