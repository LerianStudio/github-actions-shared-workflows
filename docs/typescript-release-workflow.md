# TypeScript Release Workflow

Reusable workflow for TypeScript/Node.js semantic versioning and automated release management. Creates releases based on conventional commits with GPG signing, GitHub Packages authentication for private `@lerianstudio` dependencies, and monorepo support.

## Features

- **Semantic versioning**: Automatic version calculation from conventional commits
- **GPG signing**: Signed commits and tags for security
- **GitHub App authentication**: Higher rate limits and better security
- **GitHub Packages support**: Automatic `.npmrc` configuration for private `@lerianstudio/*` dependencies
- **Clean package.json**: Overwrites existing `package.json` to avoid dependency resolution conflicts
- **Monorepo support**: Detects changed paths and runs release for each changed app
- **Branch strategy**: Pre-configured for `main` (production), `develop` (beta), and `release-candidate` (rc)
- **Dry-run mode**: Test releases safely without creating tags or GitHub releases
- **Backmerge support**: Automatic backmerging of releases
- **Slack notifications**: Configurable release status notifications

## Why Use This Instead of `release.yml`?

The generic `release.yml` uses `npm init -y` which preserves the existing `package.json`. For TypeScript projects with private `@lerianstudio/*` dependencies, this causes `npm install` to attempt resolving all dependencies (including private ones), resulting in **401 Unauthorized** errors during the release step.

`typescript-release.yml` solves this by:
1. Configuring `.npmrc` with GitHub Packages authentication (when `GH_PAT_FOR_PACKAGES` secret is available)
2. Overwriting `package.json` with a minimal version that only contains what semantic-release needs
3. Removing `package-lock.json` to prevent stale dependency resolution

## Usage

### Basic Example

```yaml
name: Release
on:
  push:
    branches:
      - develop
      - release-candidate
      - main
    tags-ignore:
      - '**'
    paths-ignore:
      - '**.md'
      - 'docs/**'
      - 'LICENSE'
      - '.gitignore'

permissions:
  contents: write
  pull-requests: write

jobs:
  release:
    name: Create Release
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/typescript-release.yml@v1.0.0
    secrets: inherit
```

### With Custom Runner and Node Version

```yaml
jobs:
  release:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/typescript-release.yml@v1.0.0
    with:
      runner_type: "blacksmith-4vcpu-ubuntu-2404"
      node_version: "22"
    secrets: inherit
```

### Dry-Run Mode (Safe Testing)

```yaml
jobs:
  release:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/typescript-release.yml@v1.0.0
    with:
      dry_run: true
    secrets: inherit
```

This runs semantic-release without creating tags, GitHub releases, or pushing commits. Useful for validating the release configuration on a new branch or after workflow changes.

### Monorepo Configuration

```yaml
jobs:
  release:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/typescript-release.yml@v1.0.0
    with:
      filter_paths: |
        apps/api
        apps/worker
        packages/shared
      path_level: "2"
    secrets: inherit
```

### Complete Release Pipeline

```yaml
name: Release Pipeline
on:
  push:
    branches: [develop, release-candidate, main]
    tags-ignore: ['**']
    paths-ignore:
      - '**.md'
      - 'docs/**'
      - 'LICENSE'

permissions:
  contents: write
  pull-requests: write

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm test

  release:
    needs: test
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/typescript-release.yml@v1.0.0
    with:
      runner_type: "blacksmith-4vcpu-ubuntu-2404"
      node_version: "20"
    secrets: inherit
```

## Inputs

| Input | Type | Default | Required | Description |
|-------|------|---------|----------|-------------|
| `semantic_version` | string | `23.0.8` | No | Semantic release version to use |
| `runner_type` | string | `blacksmith-4vcpu-ubuntu-2404` | No | GitHub runner type |
| `node_version` | string | `20` | No | Node.js version to use |
| `filter_paths` | string | `''` | No | Newline-separated list of path prefixes for monorepo filtering |
| `path_level` | string | `2` | No | Limits the path to the first N segments (e.g., `2` → `apps/agent`) |
| `dry_run` | boolean | `false` | No | Run semantic-release in dry-run mode (no tags/releases created) |

## Secrets

### Required Secrets

| Secret | Description |
|--------|-------------|
| `LERIAN_STUDIO_MIDAZ_PUSH_BOT_APP_ID` | GitHub App ID for authentication |
| `LERIAN_STUDIO_MIDAZ_PUSH_BOT_PRIVATE_KEY` | GitHub App private key |
| `LERIAN_CI_CD_USER_GPG_KEY` | GPG private key for signing commits |
| `LERIAN_CI_CD_USER_GPG_KEY_PASSWORD` | GPG key passphrase |
| `LERIAN_CI_CD_USER_NAME` | Git committer name |
| `LERIAN_CI_CD_USER_EMAIL` | Git committer email |
| `SLACK_WEBHOOK_URL` | Slack webhook for notifications |

### Optional Secrets

| Secret | Description |
|--------|-------------|
| `GH_PAT_FOR_PACKAGES` | Personal Access Token with `read:packages` scope for GitHub Packages. When provided, configures `.npmrc` for `@lerianstudio` scoped packages. |

## Outputs

| Output | Description |
|--------|-------------|
| `gpg_fingerprint` | GPG key fingerprint used for signing |

## Branch Strategy

The workflow generates a `.releaserc.json` with pre-configured branch settings:

### develop → Beta Releases

Commits to `develop` branch create beta pre-releases:
- Version: `v1.2.3-beta.1`
- Pre-release: Yes
- Use case: Development testing

### release-candidate → RC Releases

Commits to `release-candidate` branch create RC pre-releases:
- Version: `v1.2.3-rc.1`
- Pre-release: Yes
- Use case: Staging/UAT testing

### main → Production Releases

Commits to `main` branch create production releases:
- Version: `v1.2.3`
- Pre-release: No
- Use case: Production deployment

## Jobs

### prepare

Determines which apps need releases:
- **Single app mode** (default): When `filter_paths` is empty, releases from repository root
- **Monorepo mode**: When `filter_paths` is provided, detects changed paths and builds a matrix

Also skips releases for `[skip ci]` and changelog update commits.

### publish_release

Runs semantic-release for each app in the matrix:
1. Create GitHub App token
2. Checkout repository with full history
3. Sync with remote branch
4. Import GPG key for commit signing
5. Setup Node.js
6. Configure `.npmrc` for GitHub Packages (conditional)
7. Initialize clean `package.json` and `.releaserc.json`
8. Install semantic-release plugins
9. Run semantic-release

### notify

Sends Slack notification with release status. Skipped when no changes are detected or when the commit triggers a skip.

## Semantic Release Plugins

### Included Plugins

| Plugin | Version | Description |
|--------|---------|-------------|
| `@semantic-release/exec` | `7.1.0` | Execute custom scripts during release |
| `conventional-changelog-conventionalcommits` | `7.0.2` | Conventional commits support |
| `@saithodev/semantic-release-backmerge` | `4.0.1` | Automatic backmerging of releases |

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
refactor: simplify authentication logic
```

No version bump, but included in changelog.

## Troubleshooting

### 401 Unauthorized During npm install

**Issue**: `npm install` fails with 401 when resolving `@lerianstudio/*` packages

**Solutions**:
1. Ensure `GH_PAT_FOR_PACKAGES` secret is configured in the repository
2. Verify the PAT has `read:packages` scope
3. Check that the token has access to the `@lerianstudio` organization packages

### Release Not Created

**Issue**: Workflow runs but no release is created

**Solutions**:
1. Check commit messages follow conventional commits format
2. Verify you're pushing to a configured branch (`main`, `develop`, or `release-candidate`)
3. Check if version already exists as a tag
4. Review semantic-release logs in the workflow run
5. Try running with `dry_run: true` to see what semantic-release would do

### Final Release Created on develop

**Issue**: A production tag (e.g., `v1.0.0`) was created from the `develop` branch instead of a beta tag

**Solutions**:
1. This workflow generates `.releaserc.json` automatically with correct branch config — ensure you're not overriding it with a local `.releaserc` file in your repository
2. Verify the workflow version you're using has the branch prerelease configuration

### GPG Signing Failed

**Issue**: Cannot sign commits with GPG key

**Solutions**:
1. Verify GPG key is valid and hasn't expired
2. Check passphrase is correct
3. Verify key format is ASCII armored

### Skipped Release

**Issue**: Workflow is skipped unexpectedly

**Solutions**:
1. Check if commit message contains `[skip ci]`
2. Check if commit message matches `chore(release): Update CHANGELOGs`
3. For monorepo mode, verify files were changed in the configured `filter_paths`

## Differences from Generic `release.yml`

| Feature | `release.yml` | `typescript-release.yml` |
|---------|---------------|--------------------------|
| `.npmrc` setup | No | Yes (conditional on `GH_PAT_FOR_PACKAGES`) |
| `package.json` init | `npm init -y` (preserves existing) | Clean overwrite (minimal JSON) |
| Node.js version | Hardcoded `20` | Configurable via `node_version` input |
| Dry-run mode | Not available | Available via `dry_run` input |
| `.releaserc.json` | Not generated | Auto-generated with branch strategy |
| Plugin versions | Unpinned | Pinned for reproducibility |

## Related Workflows

- [Release Workflow](release-workflow.md) - Generic release workflow (Go/other languages)
- [Go Release](go-release-workflow.md) - Go-specific release with GoReleaser
- [TypeScript CI](typescript-ci-workflow.md) - TypeScript continuous integration

---

**Last Updated:** 2026-03-04
**Version:** 1.0.0
