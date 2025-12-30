# GPT Changelog Workflow

Reusable workflow for generating CHANGELOG.md using AI. Uses OpenRouter API (GPT-4o by default) to analyze commits and generate human-readable, categorized changelogs.

## Features

- **AI-powered changelog generation**: Uses OpenRouter API (GPT-4o) for intelligent commit analysis
- **Consolidated changelog**: Single CHANGELOG.md with sections per app (no overwrites)
- **Monorepo support**: Automatic detection of changed components via filter_paths
- **GitHub Release integration**: Automatically updates release notes per app tag
- **GPG signing**: Signed commits for changelog PRs
- **Tag-based versioning**: Handles between-tags, first-tag, and no-tags scenarios
- **Automatic PR creation**: Creates and optionally auto-merges changelog PRs
- **Slack notifications**: Automatic success/failure notifications

## Usage

### Single App Repository (Recommended - After Release)

Trigger changelog generation after your Release workflow completes on main:

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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gptchangelog.yml@main
    with:
      runner_type: "blacksmith-4vcpu-ubuntu-2404"
    secrets: inherit
```

> **Note**: By default, `stable_releases_only: true` means changelog is only generated for stable releases (v1.0.0), not prereleases (v1.0.0-beta.1).

### Single App Repository (Tag Push Trigger)

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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gptchangelog.yml@main
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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gptchangelog.yml@main
    with:
      runner_type: "blacksmith"
      filter_paths: |-
        charts/agent
        charts/control-plane
        charts/midaz
        charts/reporter
      path_level: '2'
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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/release.yml@main
    secrets: inherit

  changelog:
    needs: release
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gptchangelog.yml@main
    with:
      runner_type: "blacksmith"
    secrets: inherit
```

## Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `runner_type` | string | `blacksmith` | GitHub runner type |
| `filter_paths` | string | `''` | Newline-separated list of path prefixes. If empty, single-app mode |
| `path_level` | string | `2` | Directory depth for app name extraction |
| `stable_releases_only` | boolean | `true` | Only generate changelogs for stable releases (skip beta/rc/alpha) |
| `openai_model` | string | `openai/gpt-4o` | OpenRouter model for changelog generation |
| `max_context_tokens` | string | `80000` | Maximum context tokens for API |

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

1. **Detect all changed apps** via `changed-paths` action
2. **Single job iterates** through all changed apps
3. **Accumulates changelog entries** per app into one consolidated file
4. **Creates one PR** with all changes

**Result:** One CHANGELOG.md at repo root with sections for each app that changed.

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

### prepare
- Detects changed paths (monorepo) or sets single-app mode
- Outputs matrix for changelog generation job

### generate_changelog
- Installs gptchangelog and dependencies
- Iterates through all changed apps in a single job
- Generates consolidated CHANGELOG.md with sections per app
- Updates GitHub Release for each app's tag
- Creates PR with changelog update (GPG-signed)
- Auto-merges PR if possible

### notify
- Sends Slack notification on completion
- Skipped if `SLACK_WEBHOOK_URL` not configured

## Best Practices

### 1. Trigger After Release

Run changelog generation after the release workflow:

```yaml
changelog:
  needs: release
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gptchangelog.yml@main
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
1. Check OpenAI API key is valid
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
3. Try reducing `max_context_tokens`
4. Ensure model name is valid (e.g., `openai/gpt-4o`)

### Monorepo changes not detected

**Issue**: No apps in matrix for monorepo

**Solutions**:
1. Verify `filter_paths` matches your directory structure
2. Check `path_level` is correct
3. Ensure changes are in tracked paths
4. Review changed-paths action output

## Examples

### Basic Single App

```yaml
name: Changelog
on:
  push:
    tags: ['v*']

jobs:
  changelog:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gptchangelog.yml@main
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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gptchangelog.yml@main
    with:
      filter_paths: |-
        charts/agent
        charts/control-plane
        charts/midaz
        charts/reporter
      path_level: '2'
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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gptchangelog.yml@main
    with:
      filter_paths: |-
        services/api
        services/worker
        services/scheduler
      path_level: '2'
    secrets: inherit
```

### Custom OpenRouter Model

```yaml
changelog:
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gptchangelog.yml@main
  with:
    openai_model: 'anthropic/claude-3.5-sonnet'
    max_context_tokens: '128000'
  secrets: inherit
```

## Related Workflows

- [Release](release-workflow.md) - Create releases that trigger changelog generation
- [Build](build-workflow.md) - Build Docker images after release
- [Slack Notify](slack-notify-workflow.md) - Notification system
