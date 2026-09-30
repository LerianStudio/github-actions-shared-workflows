# GPT Changelog Workflow

Reusable workflow for generating CHANGELOG.md using AI. Uses OpenRouter API (GPT-4o by default) to analyze commits and generate human-readable, categorized changelogs.

## Features

- **AI-powered changelog generation**: Uses OpenRouter API (GPT-4o) for intelligent commit analysis
- **Consolidated changelog**: Single CHANGELOG.md with sections per app (no overwrites)
- **Monorepo support**: Automatic detection of changed components via filter_paths
- **GitHub Release integration**: Automatically updates release notes per app tag
- **GPG signing**: Signed commits pushed to the release line
- **Tag-based versioning**: Handles between-tags, first-tag, and no-tags scenarios
- **Release-line aware**: Resolves which branch the tag belongs to (default branch, `main`/`master`, or a `maintenance/*` / `release/*` line) instead of assuming the default branch
- **Backmerge**: Syncs the release line into `develop` after the CHANGELOG lands
- **Slack notifications**: Automatic success/failure notifications

> This workflow is a thin caller over the [`src/changelog/gptchangelog`](../src/changelog/gptchangelog/action.yml)
> composite action, which holds the implementation. `release.yml` calls the same composite,
> so both paths share one behaviour.

## Prerequisites

### Disable semantic-release changelog plugin

When using GPT Changelog, you **must disable** the `@semantic-release/changelog` plugin in your `.releaserc.yml` to avoid conflicts:

```yaml
# .releaserc.yml
plugins:
  - "@semantic-release/commit-analyzer"
  - "@semantic-release/release-notes-generator"
  # Changelog disabled - using GPT Changelog instead
  # - "@semantic-release/changelog"
  - - "@semantic-release/github"
    - successComment: "🎉 This PR is included in version ${nextRelease.gitTag}"
```

If both are enabled, you'll get duplicate or conflicting changelog entries.

## Usage

### Single App Repository (Recommended - After Release)

Trigger changelog generation after your Release workflow completes on main. This is the **recommended approach** because it:
- Avoids race conditions (only runs once after release completes)
- Ensures the release tag exists before generating changelog
- Prevents duplicate workflow runs

```yaml
name: GPT Changelog
on:
  workflow_run:
    workflows: ["Release"]
    types: [completed]
    branches: [main]
  workflow_dispatch:

permissions:
  contents: write
  pull-requests: write

jobs:
  changelog:
    if: github.event_name == 'workflow_dispatch' || github.event.workflow_run.conclusion == 'success'
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gptchangelog.yml@tier-1
    with:
      runner_type: "blacksmith-4vcpu-ubuntu-2404"
    secrets: inherit
```

> **Note**: By default, `stable_releases_only: true` means changelog is only generated for stable releases (v1.0.0), not prereleases (v1.0.0-beta.1).

### Single App Repository (Tag Push Trigger)

> **Warning**: Using `push: tags` can cause race conditions if your release workflow also triggers on tags. Both workflows may run simultaneously, causing duplicate runs or upload conflicts. Prefer `workflow_run` trigger above.

```yaml
name: Generate Changelog
on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write
  pull-requests: write

jobs:
  changelog:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gptchangelog.yml@tier-1
    with:
      runner_type: "blacksmith-4vcpu-ubuntu-2404"
    secrets: inherit
```

**Output:**
```markdown
# Changelog

## [2025-12-12]

### my-app v1.2.0

#### ✨ Features
- Added new authentication flow
- Implemented caching layer

#### 🛠 Fixes
- Fixed memory leak in worker process

---
```

### Monorepo with Multiple Components

Works with any directory structure (Helm charts, microservices, packages, etc.):

```yaml
name: Generate Changelog
on:
  push:
    tags:
      - '**-v*'  # Matches: agent-v1.0.0, midaz-v2.1.0, etc.

permissions:
  contents: write
  pull-requests: write

jobs:
  changelog:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gptchangelog.yml@tier-1
    with:
      runner_type: "blacksmith"
      filter_paths: |-
        charts/agent
        charts/control-plane
        charts/midaz
        charts/reporter
    secrets: inherit
```

**Output (when multiple apps change):**
```markdown
# Changelog

## [2025-12-12]

### agent v1.2.0

#### ✨ Features
- Added new metric collection endpoint

#### 🛠 Fixes
- Fixed reconnection logic

### midaz v2.1.0

#### ✨ Features
- New transaction batching API

#### 🚀 Improvements
- Optimized database queries

### control-plane v1.5.0

#### 🛠 Fixes
- Fixed race condition in scheduler

---
```

**Key Benefit:** All apps are consolidated into ONE CHANGELOG.md - no more overwrites when multiple apps change!

### After Release Workflow

```yaml
name: Release Pipeline
on:
  push:
    branches:
      - main

jobs:
  release:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/release.yml@tier-1
    secrets: inherit

  changelog:
    needs: release
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gptchangelog.yml@tier-1
    with:
      runner_type: "blacksmith"
    secrets: inherit
```

## Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `runner_type` | string | `blacksmith` | GitHub runner type |
| `filter_paths` | string | `''` | Newline-separated list of path prefixes. If empty, single-app mode |
| `stable_releases_only` | boolean | `true` | Only generate changelogs for stable releases (skip beta/rc/alpha) |
| `openai_model` | string | `openai/gpt-4o` | OpenRouter model for changelog generation |
| `changelog_release_branch` | string | `''` | Branch whose tags get a changelog. Empty resolves it from the run — see [Release line resolution](#release-line-resolution). A value that does not exist on origin fails the job |
| `bot_ignore_list` | string | `''` | Extra space-separated login substrings to exclude from contributors. Logins ending in `[bot]` are always excluded |
| `backmerge_enabled` | boolean | `true` | Backmerge the release line into `backmerge_target` after the CHANGELOG is committed |
| `backmerge_target` | string | `develop` | Branch to backmerge the release line into. Skipped when it does not exist on origin |

### Deprecated inputs

Still accepted so existing callers keep working, but they have no effect:

| Input | Why |
|-------|-----|
| `shared_paths` | App selection comes from which stable tags exist on the release line, not from changed files |
| `path_level` | App names are the basename of each `filter_paths` entry |
| `max_context_tokens` | Never wired to the API call, in this workflow or the composite |

## Secrets

All secrets are inherited via `secrets: inherit`. Required secrets in your repository:

| Secret | Description |
|--------|-------------|
| `OPENROUTER_API_KEY` | OpenRouter API key for AI model access |
| `LERIAN_STUDIO_MIDAZ_PUSH_BOT_APP_ID` | GitHub App ID for authentication |
| `LERIAN_STUDIO_MIDAZ_PUSH_BOT_PRIVATE_KEY` | GitHub App private key |
| `LERIAN_CI_CD_USER_GPG_KEY` | GPG private key for signing commits |
| `LERIAN_CI_CD_USER_GPG_KEY_PASSWORD` | GPG key passphrase |
| `LERIAN_CI_CD_USER_NAME` | Git committer name |
| `LERIAN_CI_CD_USER_EMAIL` | Git committer email |
| `SLACK_WEBHOOK_URL` | *(Optional)* Slack webhook for notifications |

## How It Works

### Consolidated Changelog Architecture

Unlike traditional matrix-based approaches where each app generates its own changelog (causing overwrites), this workflow uses a **single-job consolidated approach**:

1. **Resolve the release line** and check the tag is a stable release on it
2. **Build the app list** — single-app mode, or one entry per `filter_paths` directory that has a stable tag on that line
3. **Single job iterates** through every app, writing its `CHANGELOG.md` and updating its GitHub Release notes
4. **Commits and pushes** the CHANGELOGs directly to the release line (GPG-signed, with rebase-retry on a push race)

**Result:** a per-app `CHANGELOG.md` in each app's folder, committed straight to the branch the release was cut from.

> **Changed in the composite migration:** earlier versions of this workflow opened a
> `release/update-changelog-*` PR and auto-merged it. The CHANGELOG commit now goes directly
> to the release line, matching `release.yml`. If your default branch blocks direct pushes,
> the push bot app needs bypass permission.

### Release line resolution

The tag's release line is resolved in three steps, first hit wins:

1. `changelog_release_branch`, when the caller sets it
2. the branch that triggered the run, for branch/`workflow_run` triggers
3. for tag-triggered runs, the first of `<default branch>`, `main`, `master`, `maintenance/*`, `release/*` that contains the tag commit

If none matches, the run skips with an explicit message rather than publishing an empty
changelog. Earlier versions tested containment **only** against the default branch, which
silently produced empty release notes on repositories that keep `develop` as the default and
cut stable on `main`, and on any patch cut from an older minor.

### Version Range Detection

The workflow automatically determines the commit range for changelog generation:

| Scenario | Range | Example |
|----------|-------|---------|
| Two or more tags | Previous tag → Current tag | `v1.0.0...v1.1.0` |
| First tag | First commit → Current tag | `abc123...v1.0.0` |
| No tags | First commit → HEAD | `abc123...HEAD` |

### Monorepo Tag Patterns

For monorepos, the workflow supports app-specific tags:

| App | Tag Pattern | Example |
|-----|-------------|---------|
| agent | `agent-v*` | `agent-v1.0.0` |
| control-plane | `control-plane-v*` | `control-plane-v2.1.0` |

This works with **any directory structure**:
- `apps/api`, `apps/worker` → tags: `api-v1.0.0`, `worker-v2.0.0`
- `services/auth`, `services/billing` → tags: `auth-v1.0.0`, `billing-v1.5.0`
- `charts/midaz`, `charts/agent` → tags: `midaz-v1.0.0`, `agent-v2.0.0`

### Changelog Categories

GPTChangelog organizes commits into these categories:
- ✨ **Features**: New features added
- 🛠 **Fixes**: Bug fixes and improvements
- 📚 **Documentation**: Documentation updates
- 🚀 **Improvements**: Performance or backend optimizations
- ⚠️ **Breaking Changes**: Breaking changes
- 🙌 **Contributors**: Acknowledgments

## Workflow Jobs

### generate_changelog
- Calls the `src/changelog/gptchangelog` composite, which resolves the release line, builds
  the app list, generates each `CHANGELOG.md`, updates the GitHub Release notes and pushes
  the GPG-signed commit to the release line
- Backmerges the release line into `backmerge_target` (default `develop`) via
  `src/config/backmerge-sync`. Skipped when the target branch does not exist or when no
  CHANGELOG was updated; a merge conflict opens a PR instead of failing the release

### notify
- Sends Slack notification on completion
- Skipped if `SLACK_WEBHOOK_URL` not configured

## Best Practices

### 1. Trigger After Release

Run changelog generation after the release workflow:

```yaml
changelog:
  needs: release
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gptchangelog.yml@tier-1
  secrets: inherit
```

### 2. Use Conventional Commits

GPTChangelog works best with conventional commits:
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation
- `perf:` - Performance improvements

### 3. Configure Slack Notifications

Add `SLACK_WEBHOOK_URL` secret for team notifications.

## Troubleshooting

### No changelog generated

**Issue**: Workflow runs but no CHANGELOG.md is created

**Solutions**:
1. Check OpenRouter API key is valid (`OPENROUTER_API_KEY`)
2. Verify tag format matches expected pattern
3. Check if there are commits in the version range
4. Review workflow logs for gptchangelog errors

### Version header not updated

**Issue**: CHANGELOG shows wrong version

**Solutions**:
1. Verify tag format (should include version number)
2. Check sed command output in logs
3. Ensure CHANGELOG has standard version header format

### PR not created

**Issue**: Changelog generated but PR fails

**Solutions**:
1. Verify GitHub App has `contents: write` and `pull-requests: write` permissions
2. Check if branch already exists
3. Review PR creation step logs

### OpenRouter API errors

**Issue**: Changelog generation fails with API errors

**Solutions**:
1. Verify `OPENROUTER_API_KEY` is set correctly
2. Check API rate limits
3. Ensure model name is valid (e.g., `openai/gpt-4o`)

### Monorepo changes not detected

**Issue**: No apps in matrix for monorepo

**Solutions**:
1. Verify `filter_paths` matches your directory structure and that each entry is an existing directory
2. Check each app has a stable tag (`<app>-v*`) reachable from the release line — apps are selected by tag, not by changed files
3. Review the stability gate output: if it reports the tag commit is on none of the lines searched, set `changelog_release_branch`

### Release published with an empty changelog

**Issue**: The job reports success but the release body is empty

**Solution**: The stability gate did not resolve a release line. Check the `Check if tag is a
stable release on a supported release line` step — it names the branches it searched. Set
`changelog_release_branch` when the repository cuts stable somewhere it cannot infer.

## Examples

### Basic Single App

```yaml
name: Changelog
on:
  push:
    tags: ['v*']

jobs:
  changelog:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gptchangelog.yml@tier-1
    secrets: inherit
```

### Helm Charts Monorepo

```yaml
name: Changelog
on:
  push:
    tags: ['**-v*']

jobs:
  changelog:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gptchangelog.yml@tier-1
    with:
      filter_paths: |-
        charts/agent
        charts/control-plane
        charts/midaz
        charts/reporter
    secrets: inherit
```

### Microservices Monorepo

```yaml
name: Changelog
on:
  push:
    tags: ['**-v*']

jobs:
  changelog:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gptchangelog.yml@tier-1
    with:
      filter_paths: |-
        services/api
        services/worker
        services/scheduler
    secrets: inherit
```

### Custom OpenRouter Model

```yaml
changelog:
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gptchangelog.yml@tier-1
  with:
    openai_model: 'anthropic/claude-3.5-sonnet'
  secrets: inherit
```

## Related Workflows

- [Release](release.md) - Create releases that trigger changelog generation
- [Build](build.md) - Build Docker images after release
- [Slack Notify](slack-notify.md) - Notification system
