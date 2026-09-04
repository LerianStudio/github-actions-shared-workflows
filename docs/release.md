# Release Workflow

Reusable workflow for semantic versioning and automated release management. Creates releases based on conventional commits and manages version tags with GPG signing.

## Features

- **Semantic versioning**: Automatic version calculation from conventional commits
- **GPG signing**: Signed commits and tags for security
- **GitHub App authentication**: Higher rate limits and better security
- **Hotfix support**: Separate configuration for hotfix branches
- **Backmerge support**: Automatic backmerging of releases (falls back to creating a PR if the direct push fails due to branch divergence)
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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/release.yml@tier-1
    secrets: inherit
```

> **Required Secrets**: `LERIAN_STUDIO_MIDAZ_PUSH_BOT_APP_ID`, `LERIAN_STUDIO_MIDAZ_PUSH_BOT_PRIVATE_KEY`, `LERIAN_CI_CD_USER_GPG_KEY`, `LERIAN_CI_CD_USER_GPG_KEY_PASSWORD`, `LERIAN_CI_CD_USER_NAME`, `LERIAN_CI_CD_USER_EMAIL`

### With Custom Runner

```yaml
release:
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/release.yml@tier-1
  with:
    runner_type: "blacksmith-4vcpu-ubuntu-2404"
    semantic_version: "23.0.8"
  secrets: inherit
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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/release.yml@tier-1
    secrets: inherit
```

## Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `semantic_version` | string | `23.0.8` | Semantic release version to use |
| `runner_type` | string | `firmino-lxc-runners` | GitHub runner type |
| `publish_runner_type` | string | `''` | Optional runner override for the Release (publish) jobs only; empty falls back to `vars.GENERAL_RUNNERS`, then `runner_type` |
| `backmerge_enabled` | boolean | `true` | Backmerge the release branch into the target branch after a successful release |
| `backmerge_source` | string | `main` | Release branch eligible for backmerge; backmerge runs only when the release ref matches this |
| `backmerge_target` | string | `develop` | Branch that receives the backmerge |
| `backmerge_mode` | string | `direct-with-pr-fallback` | Backmerge strategy: `direct`, `pr`, or `direct-with-pr-fallback` |
| `dry_run` | boolean | `false` | Run semantic-release in dry-run mode (no tags/releases) and preview the backmerge instead of applying it |
| `prerelease_branches` | string | `develop,release-candidate` | Comma-separated list of branches treated as prerelease lines (beta/rc) |
| `prerelease_backmerge_sync_enabled` | boolean | `false` | Merge `backmerge_source` into a prerelease branch before calculating its next version. Independent of `backmerge_enabled`, which also gates the separate post-release backmerge on `backmerge_source` itself. Opt-in — set to `true` to enable this pre-version-calculation sync, which can skip/block a release on prerelease branches when the merge cannot complete directly |
| `enable_release_announcement` | boolean | `true` | Announce the published release to the repository Slack channel after a successful release |
| `announcement_product_name` | string | `''` | Product name displayed in the announcement. Defaults to the repository name |
| `announcement_slack_channel` | string | `''` | Slack channel that receives the announcement. Defaults to the `RELEASE_SLACK_CHANNEL` repository variable; the announcement is skipped when both are empty |
| `environment_name` | string | `''` | Overrides the per-channel deployment environment for this run. Empty keeps `stable`/`rc`/`beta` by ref — see [Deployment Environments](#deployment-environments) |

## Release Announcement

After a successful release, the `announce_release` job calls
[`release-notification.yml`](release-notification.md) to post the published tag to the
channel owned by the calling repository. Routing is per-repo — no shared workflow change
is needed to add a repository or change its channel.

### Setup in the consuming repository

```
Settings → Secrets and variables → Actions → New repository secret
Name:  RELEASE_WEBHOOK_URL
Value: https://hooks.slack.com/services/xxx/yyy/zzz

Settings → Secrets and variables → Actions → Variables → New repository variable
Name:  RELEASE_SLACK_CHANNEL
Value: lerian-product-release
```

`RELEASE_WEBHOOK_NOTIFICATION_URL` is still accepted as a fallback for repositories that
already use that name.

### Behavior

| Condition | Result |
|---|---|
| Channel and webhook configured | Announcement is sent for the published tag |
| No channel (input and `RELEASE_SLACK_CHANNEL` both empty) | Job is skipped |
| Channel set but no webhook secret | Job runs, notification step is skipped (non-fatal) |
| Tag type not in `RELEASE_NOTIFY_TAG_TYPES` | Job runs, notification step is skipped (non-fatal) |
| `dry_run: true` | Payload is printed, nothing is sent |
| No release published in the run | Job is skipped |

Every published tag is announced by default. To announce only some tag types —
`stable` only, or `rc,stable` — set the `RELEASE_NOTIFY_TAG_TYPES` variable at the
organization level and override it per repository as needed. See
[Tag granularity](release-notification.md#tag-granularity--release_notify_tag_types).

The announced tag comes from `publish_release_status.outputs.release_git_tag`, so monorepo
runs announce the tag actually published by the last matrix leg instead of the newest
release in the repository.

### Discord

Discord is intentionally not wired into this job. The underlying action
(`SethCohen/github-releases-to-discord`) reads the `release` event payload, which is absent
on the `push` event that drives this workflow. Keep Discord announcements on a dedicated
caller workflow that triggers `release-notification.yml` with `on: release`.

> Repositories that already announce releases through a separate `on: release` workflow will
> get two messages once this job is active. Remove the standalone Slack announcement there,
> or set `enable_release_announcement: false`.

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

### Optional Secrets

| Secret | Description |
|--------|-------------|
| `NPM_TOKEN` | npm registry auth token, forwarded to the `Semantic Release` step. Only needed when the caller's own `.releaserc` includes `@semantic-release/npm` (a package with independent semver that publishes to an npm registry). Omit for repos that do not publish to npm. |
| `RELEASE_WEBHOOK_URL` | Slack webhook that receives the release announcement. Falls back to `RELEASE_WEBHOOK_NOTIFICATION_URL`; the announcement step is skipped when both are empty. |

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

### Deployment Environments

The release jobs run under a GitHub Environment named after the channel, mirroring the branch strategy above:

| Ref | Environment | Release |
|---|---|---|
| `main` | `stable` | `v1.2.3` |
| `release-candidate` | `rc` | `v1.2.3-rc.1` |
| anything else (`develop`, …) | `beta` | `v1.2.3-beta.1` |

**Adding one of your own.** If a ref needs an environment outside those three, pass `environment_name`. It overrides the calculation for that run, so scope it with your own expression and the split keeps applying everywhere else:

```yaml
jobs:
  release:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/release.yml@tier-1
    with:
      environment_name: ${{ github.ref_name == 'sandbox' && 'sandbox' || '' }}
    secrets: inherit
```

It is one input rather than a ref-to-environment map because a run is on exactly one ref — the caller already knows which, and expressing it as a condition is both shorter and more flexible than any mapping this workflow could offer. If the environment you name has a branch policy that does not allow the ref, the job fails; that is the policy doing its job, not a bug.

**The environments belong to your repository, not to this one.** A reusable workflow's jobs run in the caller's context, so `environment: stable` resolves against *your* repo. GitHub creates each on first use, with **no protection rules and no branch policy** — they start as deployment history and nothing more.

A consequence worth knowing: you only get the environments your branching actually uses. A repository that never pushes to `release-candidate` never gets an `rc` environment, because GitHub creates one only when a job referencing it runs.

**Configuring them is your repo's job.** If you want the environments to mean something rather than just record history, add a deployment branch policy (`main` for `stable`, `release-candidate` for `rc`, `develop` for `beta`), environment secrets scoped per channel, or required reviewers to gate cutting a stable release.

**Turn off administrator bypass if the restriction has to hold.** *Allow administrators to bypass configured protection rules* is checked by default. It clearly covers required reviewers and the wait timer; whether it also covers the deployment branch policy is not something to bet on either way, so if the branch restriction must apply to everyone, uncheck it rather than relying on the default.

What the policy does buy, regardless: it is the environment — not the expression that picked its name — that decides whether a ref may deploy. That is why the branch policy, and not the naming, is what actually enforces where a release runs from.

Repositories released by an earlier version of this workflow will still have an orphaned `create_release` environment holding the old history, from when a single environment served every branch. It is inert and safe to delete once you no longer need that history.

**If you scoped secrets or variables to `create_release`, move them first.** The release jobs no longer run under that environment, so anything reachable only from it becomes unavailable and the publish, changelog, backmerge or major-tag step fails. Copy them to the channel environments that need them (`stable`, `rc`, `beta`), or to repository scope if every channel should see them, before this change reaches your repository.

Ten repositories were sampled when this split was made — `midaz`, `matcher`, `lerian-map`, `lib-commons`, `lib-streaming`, the two boilerplates and three plugins — and all had zero secrets and zero variables on `create_release`, so for most repositories this is a no-op. Check yours rather than assuming:

```bash
# {owner}/{repo} are resolved by gh from the current checkout — this repository
# is public and the workflow is consumed outside the LerianStudio org, so the
# check must not name one.
gh api 'repos/{owner}/{repo}/environments/create_release/secrets'   --jq '.total_count'
gh api 'repos/{owner}/{repo}/environments/create_release/variables' --jq '.total_count'
```

## Configuration

The workflow uses `.releaserc.yml` for all branches (no separate hotfix configuration).

**Configuration file**: `.releaserc.yml` in repository root

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

## Configuration File Example

### .releaserc.yml

Single configuration file for all branches:

```yaml
branches:
  - name: main
  - name: release-candidate
    prerelease: rc
  - name: develop
    prerelease: beta

plugins:
  - - "@semantic-release/commit-analyzer"
    - preset: conventionalcommits
      releaseRules:
        - type: feat
          release: minor
        - type: fix
          release: patch
        - type: perf
          release: patch
        - breaking: true
          release: major
  - "@semantic-release/release-notes-generator"
  - "@semantic-release/changelog"
  - "@semantic-release/github"
```

> **Migration:** backmerge is now orchestrated by the workflow, not by semantic-release. Remove any `@saithodev/semantic-release-backmerge` plugin entry from your `.releaserc` and configure backmerge through the `backmerge_*` workflow inputs instead.

## Workflow Steps

1. **Create GitHub App Token**: Generate authentication token with higher rate limits
2. **Checkout Repository**: Clone with full history for versioning
3. **Sync with Remote**: Ensure latest changes are pulled
4. **Fetch git notes**: Fetch `refs/notes/*` so semantic-release can resolve which prerelease channels each tag was published to (required to promote a prerelease to stable on the release branch)
5. **Import GPG Key**: Import and configure GPG key for signing
6. **Initialize package.json**: Create if doesn't exist
7. **Install Plugins**: Install semantic-release plugins
8. **Run Semantic Release**: Calculate version and create release using `.releaserc.yml`

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
- `GPG_PRIVATE_KEY`: Contents of `private-key.asc`
- `GPG_KEY_PASSWORD`: Key passphrase

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
   - **Name**: `My CI/CD Bot`
   - **Homepage URL**: Your organization URL
   - **Permissions**:
     - Contents: Read & Write
     - Pull Requests: Read & Write
     - Metadata: Read-only
4. Generate private key
5. Install app to repositories
6. Add to secrets:
   - `GITHUB_APP_ID`: App ID
   - `GITHUB_APP_PRIVATE_KEY`: Private key contents

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
    branches: [develop, release-candidate, main]

jobs:
  release:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/release.yml@tier-1
    secrets: inherit
```

### Release with Build Pipeline

```yaml
name: Release Pipeline
on:
  push:
    branches: [develop, release-candidate, main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: make test

  release:
    needs: test
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/release.yml@tier-1
    secrets: inherit

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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/release.yml@tier-1
    secrets: inherit
```

## Semantic Release Plugins

### Included Plugins

- **@semantic-release/commit-analyzer**: Analyzes commits to determine version bump
- **@semantic-release/release-notes-generator**: Generates release notes from commits
- **@semantic-release/github**: Creates GitHub releases
- **@semantic-release/exec**: Executes custom scripts (installed automatically)
- **conventional-changelog-conventionalcommits**: Conventional commits support

Backmerging is no longer handled by a semantic-release plugin. After a successful release, the workflow runs the `backmerge-sync` composite action (controlled by the `backmerge_*` inputs) to sync `backmerge_source` into `backmerge_target`. Behavior depends on `backmerge_mode`: `direct` (fail on conflict), `pr` (always open a PR), or `direct-with-pr-fallback` (attempt a direct merge, open a PR on conflict or rejected push).

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

- [GitOps Update](gitops-update.md) - Update deployments after release
- [PR Security Scan](pr-security-scan.md) - Security checks before release
- [API Dog E2E Tests](api-dog-e2e-tests.md) - E2E tests after release
