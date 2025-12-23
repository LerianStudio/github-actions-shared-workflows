# GPTChangelog Workflow Implementation Plan

> **For Agents:** REQUIRED SUB-SKILL: Use ring-default:executing-plans to implement this plan task-by-task.

**Goal:** Create a reusable workflow that generates a consolidated CHANGELOG.md and RELEASE_NOTES.md using GPTChangelog, with full monorepo support for any multi-app repositories (helm charts, microservices, etc.).

**Architecture:** The workflow follows the established shared workflows pattern with a `prepare` → `main_job` → `notify` structure. For monorepos, it uses the `LerianStudio/github-actions-changed-paths` action to detect which apps changed and generates a **single consolidated changelog** with sections per app. For single-app repos, it generates a changelog for the entire repository.

**Key Design Decision - Consolidated Changelog:**
- Single CHANGELOG.md at repository root (not per-app files)
- When multiple apps change, each app gets its own section in the changelog
- Prevents overwrite issues when multiple apps change simultaneously
- Works generically with any directory structure (charts, apps, services, etc.)

**Tech Stack:** GitHub Actions reusable workflow, Python 3.10, gptchangelog PyPI package, OpenAI GPT-4o, GPG signing, GitHub App authentication

**Global Prerequisites:**
- Environment: GitHub Actions runner (blacksmith default)
- Tools: Git, Python 3.10+, pip
- Access: OpenAI API key, GitHub App credentials, GPG key for signing
- State: Feature branch created from `develop` branch

**Verification before starting:**
```bash
# Navigate to the shared-workflows repository
cd /Users/ferr3ira/Documents/empresas/lerian-studio/projetos/github/modules/github-actions-shared-workflows

# Verify clean git state
git status  # Expected: clean working tree or known changes

# Verify on develop branch
git branch --show-current  # Expected: develop or main

# Verify docs/plans directory exists
ls docs/plans/  # Expected: directory exists with existing plans
```

---

## Task 1: Create Feature Branch

**Files:**
- None (git operation)

**Prerequisites:**
- Tools: Git
- Current directory: `/Users/ferr3ira/Documents/empresas/lerian-studio/projetos/github/modules/github-actions-shared-workflows`

**Step 1: Fetch latest changes**

```bash
cd /Users/ferr3ira/Documents/empresas/lerian-studio/projetos/github/modules/github-actions-shared-workflows
git fetch origin
```

**Step 2: Create feature branch from develop**

```bash
git checkout develop
git pull origin develop
git checkout -b feature/gptchangelog-workflow
```

**Expected output:**
```
Switched to a new branch 'feature/gptchangelog-workflow'
```

**Step 3: Verify branch creation**

Run: `git branch --show-current`

**Expected output:**
```
feature/gptchangelog-workflow
```

**If Task Fails:**

1. **Branch already exists:**
   - Run: `git branch -D feature/gptchangelog-workflow`
   - Retry branch creation

2. **develop branch doesn't exist:**
   - Run: `git checkout main` instead
   - Continue from main branch

---

## Task 2: Create the GPTChangelog Workflow File

**Files:**
- Create: `/Users/ferr3ira/Documents/empresas/lerian-studio/projetos/github/modules/github-actions-shared-workflows/.github/workflows/gptchangelog.yml`

**Prerequisites:**
- Tools: Text editor
- Branch: `feature/gptchangelog-workflow`
- Files must exist: `.github/workflows/` directory

**Step 1: Create the workflow file**

Create the file `.github/workflows/gptchangelog.yml` with the following content:

```yaml
name: "GPT Changelog"

# This reusable workflow generates CHANGELOG.md and RELEASE_NOTES.md using GPTChangelog
# It uses OpenAI GPT-4o to analyze commits and generate human-readable changelogs
#
# Monorepo Support:
# - If filter_paths is provided: detects changes and generates changelog for each changed app
# - If filter_paths is empty: generates changelog for the entire repository (single app mode)
#
# Features:
# - Generates CHANGELOG.md with categorized changes
# - Generates RELEASE_NOTES.md and updates GitHub Release
# - Creates PR with changelog update using GPG-signed commits
# - Handles tag-based versioning (between tags, first tag, no tags scenarios)

on:
  workflow_call:
    inputs:
      runner_type:
        description: 'Runner to use for the workflow'
        type: string
        default: 'blacksmith'
      filter_paths:
        description: 'Newline-separated list of path prefixes to filter. If not provided, treats as single app repo.'
        type: string
        required: false
        default: ''
      path_level:
        description: 'Limits the path to the first N segments (e.g., 2 -> "charts/agent")'
        type: string
        default: '2'
      openai_model:
        description: 'OpenAI model to use for changelog generation'
        type: string
        default: 'gpt-4o'
      max_context_tokens:
        description: 'Maximum context tokens for OpenAI API'
        type: string
        default: '80000'
      python_version:
        description: 'Python version to use'
        type: string
        default: '3.10'

permissions:
  contents: write
  pull-requests: write

jobs:
  prepare:
    runs-on: ${{ inputs.runner_type }}
    outputs:
      matrix: ${{ steps.set-matrix.outputs.matrix }}
      has_changes: ${{ steps.set-matrix.outputs.has_changes }}
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Get changed paths (monorepo)
        if: inputs.filter_paths != ''
        id: changed-paths
        uses: LerianStudio/github-actions-changed-paths@main
        with:
          filter_paths: ${{ inputs.filter_paths }}
          path_level: ${{ inputs.path_level }}
          get_app_name: 'true'

      - name: Set matrix
        id: set-matrix
        run: |
          if [ -z "${{ inputs.filter_paths }}" ]; then
            # Single app mode - generate changelog from root
            APP_NAME="${{ github.event.repository.name }}"
            echo "matrix=[{\"name\": \"${APP_NAME}\", \"working_dir\": \".\"}]" >> $GITHUB_OUTPUT
            echo "has_changes=true" >> $GITHUB_OUTPUT
            echo "📦 Single app mode: ${APP_NAME}"
          else
            MATRIX='${{ steps.changed-paths.outputs.matrix }}'
            if [ "$MATRIX" == "[]" ] || [ -z "$MATRIX" ]; then
              echo "matrix=[]" >> $GITHUB_OUTPUT
              echo "has_changes=false" >> $GITHUB_OUTPUT
              echo "⚠️ No changes detected in filter_paths"
            else
              echo "matrix=$MATRIX" >> $GITHUB_OUTPUT
              echo "has_changes=true" >> $GITHUB_OUTPUT
              echo "📦 Monorepo mode - detected changes: $MATRIX"
            fi
          fi

  generate_changelog:
    needs: prepare
    if: needs.prepare.outputs.has_changes == 'true'
    runs-on: ${{ inputs.runner_type }}
    name: Generate Consolidated Changelog

    steps:
      - name: Create GitHub App Token
        uses: actions/create-github-app-token@v1
        id: app-token
        with:
          app-id: ${{ secrets.LERIAN_STUDIO_MIDAZ_PUSH_BOT_APP_ID }}
          private-key: ${{ secrets.LERIAN_STUDIO_MIDAZ_PUSH_BOT_PRIVATE_KEY }}

      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          token: ${{ steps.app-token.outputs.token }}

      - name: Sync with remote branch
        run: |
          git fetch origin ${{ github.ref_name }}
          git reset --hard origin/${{ github.ref_name }}

      - name: Import GPG key
        uses: crazy-max/ghaction-import-gpg@v6
        id: import_gpg
        with:
          gpg_private_key: ${{ secrets.LERIAN_CI_CD_USER_GPG_KEY }}
          passphrase: ${{ secrets.LERIAN_CI_CD_USER_GPG_KEY_PASSWORD }}
          git_committer_name: ${{ secrets.LERIAN_CI_CD_USER_NAME }}
          git_committer_email: ${{ secrets.LERIAN_CI_CD_USER_EMAIL }}
          git_config_global: true
          git_user_signingkey: true
          git_commit_gpgsign: true

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ inputs.python_version }}

      - name: Install gptchangelog
        run: |
          python -m pip install --upgrade pip
          pip install gptchangelog
          echo "✅ gptchangelog installed successfully"

      - name: Create gptchangelog config
        run: |
          mkdir -p .gptchangelog
          cat > .gptchangelog/config.ini << EOF
          [gptchangelog]
          openai = true

          [openai]
          api_key = ${OPENAI_API_KEY}
          model = ${{ inputs.openai_model }}
          max_context_tokens = ${{ inputs.max_context_tokens }}
          EOF
          echo "✅ gptchangelog config created"
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}

      - name: Create changelog prompt template
        run: |
          mkdir -p .gptchangelog/templates
          cat > .gptchangelog/templates/changelog_prompt.txt << 'EOF'
          ## Release $next_version (Released on $current_date)

          ### What's New
          $commit_messages

          ### ✨ Features
          - Highlight new features added in this release.

          ### 🛠 Fixes
          - List bug fixes and improvements.

          ### 📚 Documentation
          - Summarize updates to documentation.

          ### 🚀 Improvements
          - Highlight performance or backend optimizations.

          ### ⚠️ Breaking Changes
          - List any breaking changes here.

          ### 🙌 Contributors
          - Acknowledge contributors for this release.
          EOF
          echo "✅ Changelog prompt template created"

      - name: Generate consolidated changelog for all apps
        id: generate
        run: |
          echo "OPENAI_API_KEY=${OPENAI_API_KEY}" > .env
          git fetch --tags
          
          MATRIX='${{ needs.prepare.outputs.matrix }}'
          CURRENT_DATE=$(date +%Y-%m-%d)
          CONSOLIDATED_CHANGELOG=""
          CONSOLIDATED_RELEASE_NOTES=""
          APPS_UPDATED=""
          
          echo "📦 Processing apps from matrix: $MATRIX"
          
          # Parse the matrix JSON and iterate through each app
          echo "$MATRIX" | jq -c '.[]' | while read -r APP; do
            APP_NAME=$(echo "$APP" | jq -r '.name')
            WORKING_DIR=$(echo "$APP" | jq -r '.working_dir')
            
            echo ""
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "📝 Processing: $APP_NAME (dir: $WORKING_DIR)"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            
            # Determine tag pattern based on app type
            if [ "$WORKING_DIR" != "." ]; then
              TAG_PATTERN="${APP_NAME}-v*"
            else
              TAG_PATTERN="v*"
            fi
            
            echo "🔍 Looking for tags matching: $TAG_PATTERN"
            
            # Determine version range
            if git describe --tags --abbrev=0 --match "$TAG_PATTERN" HEAD >/dev/null 2>&1; then
              LAST_TAG=$(git describe --tags --abbrev=0 --match "$TAG_PATTERN" HEAD)
              
              if git describe --tags --abbrev=0 --match "$TAG_PATTERN" HEAD^ >/dev/null 2>&1; then
                PENULT_TAG=$(git describe --tags --abbrev=0 --match "$TAG_PATTERN" HEAD^)
                SINCE="$PENULT_TAG"
                TO="$LAST_TAG"
                echo "🟢 Range: $PENULT_TAG → $LAST_TAG"
              else
                FIRST_COMMIT=$(git rev-list --max-parents=0 HEAD)
                SINCE="$FIRST_COMMIT"
                TO="$LAST_TAG"
                echo "🟡 First tag - Range: $FIRST_COMMIT → $LAST_TAG"
              fi
            else
              FIRST_COMMIT=$(git rev-list --max-parents=0 HEAD)
              SINCE="$FIRST_COMMIT"
              TO="HEAD"
              LAST_TAG="HEAD"
              echo "🔴 No tags - Range: $FIRST_COMMIT → HEAD"
            fi
            
            # Extract version from tag
            VERSION=$(echo "$LAST_TAG" | sed 's/.*-v/v/' | sed 's/^v//')
            
            # Generate changelog for this app
            TEMP_CHANGELOG=$(mktemp)
            cd "$WORKING_DIR" 2>/dev/null || cd .
            
            gptchangelog generate \
              --since "$SINCE" \
              --to "$TO" \
              --output "$TEMP_CHANGELOG" || {
                echo "⚠️ Failed to generate changelog for $APP_NAME"
                continue
              }
            
            # Clean up markdown blocks
            sed -i '/^```/d' "$TEMP_CHANGELOG"
            
            # Extract content (skip the header line if present)
            CONTENT=$(cat "$TEMP_CHANGELOG" | tail -n +2)
            
            # Build app section for consolidated changelog
            APP_SECTION="### ${APP_NAME} v${VERSION}

${CONTENT}
"
            # Append to consolidated files
            echo "$APP_SECTION" >> /tmp/consolidated_changelog.md
            echo "$APP_SECTION" >> /tmp/consolidated_release_notes.md
            
            # Track which apps were updated
            echo "${APP_NAME}:${VERSION}" >> /tmp/apps_updated.txt
            
            # Update GitHub Release for this app's tag (if not HEAD)
            if [ "$LAST_TAG" != "HEAD" ]; then
              echo "$APP_SECTION" > /tmp/app_release_notes.md
              gh release edit "$LAST_TAG" --notes-file /tmp/app_release_notes.md || \
                echo "⚠️ Could not update release for $LAST_TAG"
            fi
            
            cd - >/dev/null 2>&1 || true
            rm -f "$TEMP_CHANGELOG"
            
            echo "✅ Processed $APP_NAME"
          done
          
          # Create final consolidated CHANGELOG.md
          if [ -f /tmp/consolidated_changelog.md ]; then
            APPS_LIST=$(cat /tmp/apps_updated.txt 2>/dev/null | tr '\n' ', ' | sed 's/,$//')
            
            # Prepare the new changelog entry
            NEW_ENTRY="## [$CURRENT_DATE]

$( cat /tmp/consolidated_changelog.md )
---
"
            # Prepend to existing CHANGELOG.md or create new one
            if [ -f CHANGELOG.md ]; then
              # Insert after the title line
              if grep -q "^# " CHANGELOG.md; then
                TITLE=$(head -n 1 CHANGELOG.md)
                EXISTING=$(tail -n +2 CHANGELOG.md)
                echo "$TITLE

$NEW_ENTRY
$EXISTING" > CHANGELOG.md
              else
                echo "# Changelog

$NEW_ENTRY
$(cat CHANGELOG.md)" > CHANGELOG.md
              fi
            else
              echo "# Changelog

$NEW_ENTRY" > CHANGELOG.md
            fi
            
            # Create RELEASE_NOTES.md
            echo "# Release Notes - $CURRENT_DATE

$(cat /tmp/consolidated_release_notes.md)" > RELEASE_NOTES.md
            
            echo "apps_updated=$APPS_LIST" >> $GITHUB_OUTPUT
            echo "✅ Consolidated changelog created with apps: $APPS_LIST"
          else
            echo "⚠️ No changelog content generated"
            echo "apps_updated=" >> $GITHUB_OUTPUT
          fi
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          GH_TOKEN: ${{ steps.app-token.outputs.token }}

      - name: Show generated changelog
        run: |
          echo "📄 Generated CHANGELOG.md:"
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
          head -100 CHANGELOG.md
          echo ""
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

      - name: Create changelog PR
        if: steps.generate.outputs.apps_updated != ''
        run: |
          BASE_BRANCH="${GITHUB_REF##*/}"
          CURRENT_DATE=$(date +%Y-%m-%d)
          BRANCH_NAME="release/update-changelog-${CURRENT_DATE}"
          APPS_UPDATED="${{ steps.generate.outputs.apps_updated }}"
          
          echo "📌 Creating branch: $BRANCH_NAME"
          git checkout -b "$BRANCH_NAME"
          
          # Add and commit CHANGELOG
          git add CHANGELOG.md
          if ! git diff --cached --quiet; then
            git commit -S -m "chore(release): Update CHANGELOG for ${APPS_UPDATED}"
            echo "✅ CHANGELOG committed"
          else
            echo "⚠️ No changes to CHANGELOG"
            exit 0
          fi
          
          # Merge base branch to resolve conflicts
          git fetch origin "$BASE_BRANCH"
          git merge -X ours origin/"$BASE_BRANCH" --no-ff -m "Merge $BASE_BRANCH into ${BRANCH_NAME}" || {
            git checkout --ours CHANGELOG.md
            git add CHANGELOG.md
            git commit -m "resolve conflict using ours strategy"
          }
          
          # Push and create PR
          git push --force-with-lease origin "$BRANCH_NAME"
          
          if ! gh pr view "$BRANCH_NAME" --base "$BASE_BRANCH" > /dev/null 2>&1; then
            gh pr create \
              --title "chore(release): Update CHANGELOG - ${CURRENT_DATE}" \
              --body "## Automatic Changelog Update

**Date:** ${CURRENT_DATE}
**Apps Updated:** ${APPS_UPDATED}

### Changes
- Updated CHANGELOG.md with consolidated release notes
- Each app section generated by GPTChangelog using OpenAI GPT-4o

### Apps Included
$(echo "$APPS_UPDATED" | tr ',' '\n' | sed 's/^/- /')

---
*This PR was automatically generated by the GPTChangelog workflow.*" \
              --base "$BASE_BRANCH" \
              --head "$BRANCH_NAME"
            echo "✅ PR created"
          else
            echo "⚠️ PR already exists"
          fi
          
          # Auto-merge if possible
          gh pr merge --merge --delete-branch || echo "⚠️ Could not auto-merge PR"
        env:
          GH_TOKEN: ${{ steps.app-token.outputs.token }}

      - name: Cleanup sensitive files
        if: always()
        run: |
          rm -f .env
          rm -rf .gptchangelog
          rm -f /tmp/consolidated_changelog.md /tmp/consolidated_release_notes.md /tmp/apps_updated.txt /tmp/app_release_notes.md
          echo "🧹 Cleaned up sensitive files"

  # Slack notification
  notify:
    name: Notify
    needs: [prepare, generate_changelog]
    if: always() && needs.prepare.outputs.has_changes == 'true'
    uses: ./.github/workflows/slack-notify.yml
    with:
      status: ${{ needs.generate_changelog.result }}
      workflow_name: "GPT Changelog"
      failed_jobs: ${{ needs.generate_changelog.result == 'failure' && 'Generate Changelog' || '' }}
    secrets:
      SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

**Step 2: Verify file was created**

Run: `ls -la /Users/ferr3ira/Documents/empresas/lerian-studio/projetos/github/modules/github-actions-shared-workflows/.github/workflows/gptchangelog.yml`

**Expected output:**
```
-rw-r--r--  1 user  staff  XXXX  Dec XX XX:XX gptchangelog.yml
```

**If Task Fails:**

1. **Directory doesn't exist:**
   - Run: `mkdir -p .github/workflows`
   - Retry file creation

2. **Permission denied:**
   - Check file permissions
   - Run with appropriate permissions

---

## Task 3: Create the Documentation File

**Files:**
- Create: `/Users/ferr3ira/Documents/empresas/lerian-studio/projetos/github/modules/github-actions-shared-workflows/docs/gptchangelog-workflow.md`

**Prerequisites:**
- Tools: Text editor
- Branch: `feature/gptchangelog-workflow`
- Files must exist: `docs/` directory

**Step 1: Create the documentation file**

Create the file `docs/gptchangelog-workflow.md` with the following content:

```markdown
# GPT Changelog Workflow

Reusable workflow for generating CHANGELOG.md and RELEASE_NOTES.md using GPTChangelog. Uses OpenAI GPT-4o to analyze commits and generate human-readable, categorized changelogs.

## Features

- **AI-powered changelog generation**: Uses OpenAI GPT-4o for intelligent commit analysis
- **Monorepo support**: Automatic detection of changed components via filter_paths
- **GitHub Release integration**: Automatically updates release notes
- **GPG signing**: Signed commits for changelog PRs
- **Tag-based versioning**: Handles between-tags, first-tag, and no-tags scenarios
- **Automatic PR creation**: Creates and optionally auto-merges changelog PRs
- **Slack notifications**: Automatic success/failure notifications

## Usage

### Single App Repository

```yaml
name: Generate Changelog
on:
  push:
    tags:
      - 'v*'

jobs:
  changelog:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gptchangelog.yml@main
    with:
      runner_type: "blacksmith"
    secrets: inherit
```

**Output (single app):**
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

## [2025-12-01]
...
```

### Monorepo with Multiple Components (e.g., Helm Charts, Microservices)

```yaml
name: Generate Changelog
on:
  push:
    tags:
      - '**'

jobs:
  changelog:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gptchangelog.yml@main
    with:
      runner_type: "blacksmith"
      filter_paths: |-
        charts/agent
        charts/control-plane
        charts/midaz
        charts/plugin-access-manager
        charts/plugin-crm
        charts/plugin-fees
        charts/reporter
      path_level: '2'
    secrets: inherit
```

**Output (monorepo with multiple apps changed):**
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

## [2025-12-01]
...
```

**Key Benefit:** All apps are included in ONE CHANGELOG.md file - no more overwrites when multiple apps change!

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
| `openai_model` | string | `gpt-4o` | OpenAI model for changelog generation |
| `max_context_tokens` | string | `80000` | Maximum context tokens for OpenAI API |
| `python_version` | string | `3.10` | Python version to use |

## Secrets

### Required Secrets

| Secret | Description |
|--------|-------------|
| `OPENAI_API_KEY` | OpenAI API key for GPT-4o access |
| `LERIAN_STUDIO_MIDAZ_PUSH_BOT_APP_ID` | GitHub App ID for authentication |
| `LERIAN_STUDIO_MIDAZ_PUSH_BOT_PRIVATE_KEY` | GitHub App private key |
| `LERIAN_CI_CD_USER_GPG_KEY` | GPG private key for signing commits |
| `LERIAN_CI_CD_USER_GPG_KEY_PASSWORD` | GPG key passphrase |
| `LERIAN_CI_CD_USER_NAME` | Git committer name |
| `LERIAN_CI_CD_USER_EMAIL` | Git committer email |

### Optional Secrets

| Secret | Description |
|--------|-------------|
| `SLACK_WEBHOOK_URL` | Slack webhook for notifications (gracefully skipped if not provided) |

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

This works with **any directory structure** - not just charts. Examples:
- `apps/api`, `apps/worker` → tags: `api-v1.0.0`, `worker-v2.0.0`
- `services/auth`, `services/billing` → tags: `auth-v1.0.0`, `billing-v1.5.0`
- `packages/core`, `packages/utils` → tags: `core-v3.0.0`, `utils-v1.2.0`

### Generated Files

| File | Description |
|------|-------------|
| `CHANGELOG.md` | **Single consolidated** changelog with sections per app |
| `RELEASE_NOTES.md` | Release-specific notes (also consolidated) |

### Changelog Structure

```markdown
# Changelog

## [2025-12-12]

### app-1 v1.2.0
- Changes for app-1...

### app-2 v2.0.0
- Changes for app-2...

---

## [2025-12-01]
- Previous release entries...
```

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
- Generates CHANGELOG.md and RELEASE_NOTES.md
- Updates GitHub Release with release notes
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
```

### 2. Use Conventional Commits

GPTChangelog works best with conventional commits:
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation
- `perf:` - Performance improvements

### 3. Configure Slack Notifications

Add `SLACK_WEBHOOK_URL` secret for team notifications.

### 4. Review Generated Changelogs

The workflow creates PRs for review before merging. Disable auto-merge if manual review is required.

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

### OpenAI API errors

**Issue**: gptchangelog fails with API errors

**Solutions**:
1. Verify `OPENAI_API_KEY` is set correctly
2. Check API rate limits
3. Try reducing `max_context_tokens`
4. Ensure model name is valid (`gpt-4o`)

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
    tags: ['**']

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

### Custom OpenAI Model

```yaml
changelog:
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gptchangelog.yml@main
  with:
    openai_model: 'gpt-4-turbo'
    max_context_tokens: '128000'
  secrets: inherit
```

## Related Workflows

- [Release](release-workflow.md) - Create releases that trigger changelog generation
- [Build](build-workflow.md) - Build Docker images after release
- [Slack Notify](slack-notify-workflow.md) - Notification system

---

**Last Updated:** 2025-12-12
**Version:** 1.0.0
```

**Step 2: Verify file was created**

Run: `ls -la /Users/ferr3ira/Documents/empresas/lerian-studio/projetos/github/modules/github-actions-shared-workflows/docs/gptchangelog-workflow.md`

**Expected output:**
```
-rw-r--r--  1 user  staff  XXXX  Dec XX XX:XX gptchangelog-workflow.md
```

**If Task Fails:**

1. **Directory doesn't exist:**
   - Run: `mkdir -p docs`
   - Retry file creation

---

## Task 4: Update README.md with New Workflow

**Files:**
- Modify: `/Users/ferr3ira/Documents/empresas/lerian-studio/projetos/github/modules/github-actions-shared-workflows/README.md`

**Prerequisites:**
- Tools: Text editor
- Branch: `feature/gptchangelog-workflow`
- Files must exist: `README.md`

**Step 1: Read the current README.md**

Run: `cat /Users/ferr3ira/Documents/empresas/lerian-studio/projetos/github/modules/github-actions-shared-workflows/README.md`

**Step 2: Add the new workflow entry to the Available Workflows section**

Find the line `### 12. [Slack Notify]` and add the following entry AFTER it (as item 13):

```markdown
### 13. [GPT Changelog](docs/gptchangelog-workflow.md)
AI-powered changelog generation using GPTChangelog and OpenAI GPT-4o.

**Key Features**: AI commit analysis, monorepo support, GitHub Release integration, GPG signing
```

**Step 3: Verify the update**

Run: `grep -A3 "GPT Changelog" /Users/ferr3ira/Documents/empresas/lerian-studio/projetos/github/modules/github-actions-shared-workflows/README.md`

**Expected output:**
```
### 13. [GPT Changelog](docs/gptchangelog-workflow.md)
AI-powered changelog generation using GPTChangelog and OpenAI GPT-4o.

**Key Features**: AI commit analysis, monorepo support, GitHub Release integration, GPG signing
```

**If Task Fails:**

1. **Pattern not found:**
   - Check for alternate section names
   - Manually locate the workflow list section
   - Add entry at appropriate location

---

## Task 5: Commit All Changes

**Files:**
- All files created/modified in previous tasks

**Prerequisites:**
- Tools: Git
- Branch: `feature/gptchangelog-workflow`
- All files created successfully

**Step 1: Check status of changes**

Run: `cd /Users/ferr3ira/Documents/empresas/lerian-studio/projetos/github/modules/github-actions-shared-workflows && git status`

**Expected output:**
```
On branch feature/gptchangelog-workflow
Changes not staged for commit:
  modified:   README.md

Untracked files:
  .github/workflows/gptchangelog.yml
  docs/gptchangelog-workflow.md
```

**Step 2: Stage all changes**

```bash
git add .github/workflows/gptchangelog.yml
git add docs/gptchangelog-workflow.md
git add README.md
```

**Step 3: Commit changes**

```bash
git commit -m "feat: add GPTChangelog reusable workflow

- Add gptchangelog.yml reusable workflow with monorepo support
- Add comprehensive documentation in docs/gptchangelog-workflow.md
- Update README.md with new workflow entry

Features:
- AI-powered changelog generation using OpenAI GPT-4o
- Monorepo support via filter_paths and path_level
- GitHub Release notes integration
- GPG-signed commits and PRs
- Slack notification integration
- Blacksmith runner as default"
```

**Expected output:**
```
[feature/gptchangelog-workflow XXXXXXX] feat: add GPTChangelog reusable workflow
 3 files changed, XXX insertions(+)
 create mode 100644 .github/workflows/gptchangelog.yml
 create mode 100644 docs/gptchangelog-workflow.md
```

**Step 4: Verify commit**

Run: `git log --oneline -1`

**Expected output:**
```
XXXXXXX feat: add GPTChangelog reusable workflow
```

**If Task Fails:**

1. **Nothing to commit:**
   - Verify files were created correctly
   - Check git status for untracked files

2. **GPG signing required but fails:**
   - Use `git commit --no-gpg-sign` for local testing
   - Fix GPG setup before pushing

---

## Task 6: Push Branch and Create PR

**Files:**
- None (git operation)

**Prerequisites:**
- Tools: Git, GitHub CLI (gh)
- Branch: `feature/gptchangelog-workflow` with commit
- Remote: origin configured

**Step 1: Push branch to remote**

```bash
cd /Users/ferr3ira/Documents/empresas/lerian-studio/projetos/github/modules/github-actions-shared-workflows
git push -u origin feature/gptchangelog-workflow
```

**Expected output:**
```
Enumerating objects: ...
...
To github.com:LerianStudio/github-actions-shared-workflows.git
 * [new branch]      feature/gptchangelog-workflow -> feature/gptchangelog-workflow
Branch 'feature/gptchangelog-workflow' set up to track remote branch 'feature/gptchangelog-workflow' from 'origin'.
```

**Step 2: Create Pull Request**

```bash
gh pr create \
  --title "feat: add GPTChangelog reusable workflow" \
  --body "## Summary
Adds a new reusable workflow for generating CHANGELOG.md and RELEASE_NOTES.md using GPTChangelog with OpenAI GPT-4o.

## Features
- ✨ AI-powered changelog generation using OpenAI GPT-4o
- 📦 Monorepo support via \`filter_paths\` and \`path_level\` inputs
- 📝 GitHub Release notes integration
- 🔐 GPG-signed commits and PRs
- 📢 Slack notification integration
- 🏃 Blacksmith runner as default

## Files Added
- \`.github/workflows/gptchangelog.yml\` - The reusable workflow
- \`docs/gptchangelog-workflow.md\` - Comprehensive documentation

## Files Modified
- \`README.md\` - Added workflow to the list

## Usage Example

### Single App
\`\`\`yaml
changelog:
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gptchangelog.yml@main
  secrets: inherit
\`\`\`

### Monorepo (Helm Charts)
\`\`\`yaml
changelog:
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gptchangelog.yml@main
  with:
    filter_paths: |-
      charts/agent
      charts/control-plane
      charts/midaz
    path_level: '2'
  secrets: inherit
\`\`\`

## Migration from Standalone Action
This workflow replaces the standalone \`github-actions-gptchangelog\` composite action with a reusable workflow that follows the shared-workflows patterns.

## Testing
- [ ] Test with single-app repository
- [ ] Test with monorepo (helm charts)
- [ ] Verify GPG signing works
- [ ] Verify Slack notifications work" \
  --base develop \
  --head feature/gptchangelog-workflow
```

**Expected output:**
```
https://github.com/LerianStudio/github-actions-shared-workflows/pull/XX
```

**If Task Fails:**

1. **gh not authenticated:**
   - Run: `gh auth login`
   - Follow authentication steps

2. **develop branch doesn't exist as base:**
   - Use `--base main` instead

3. **PR already exists:**
   - Run: `gh pr view` to see existing PR

---

## Task 7: Run Code Review

> **Note:** This task should be run after PR creation to ensure code quality.

**Step 1: Dispatch all 3 reviewers in parallel:**
- REQUIRED SUB-SKILL: Use ring-default:requesting-code-review
- All reviewers run simultaneously (ring-default:code-reviewer, ring-default:business-logic-reviewer, ring-default:security-reviewer)
- Wait for all to complete

**Step 2: Handle findings by severity (MANDATORY):**

**Critical/High/Medium Issues:**
- Fix immediately (do NOT add TODO comments for these severities)
- Re-run all 3 reviewers in parallel after fixes
- Repeat until zero Critical/High/Medium issues remain

**Low Issues:**
- Add `TODO(review):` comments in code at the relevant location
- Format: `TODO(review): [Issue description] (reported by [reviewer] on [date], severity: Low)`

**Cosmetic/Nitpick Issues:**
- Add `FIXME(nitpick):` comments in code at the relevant location
- Format: `FIXME(nitpick): [Issue description] (reported by [reviewer] on [date], severity: Cosmetic)`

**Step 3: Proceed only when:**
- Zero Critical/High/Medium issues remain
- All Low issues have TODO(review): comments added
- All Cosmetic issues have FIXME(nitpick): comments added

---

## Summary Checklist

Before completing the implementation:

- [ ] Feature branch created from develop
- [ ] `.github/workflows/gptchangelog.yml` created with all features
- [ ] `docs/gptchangelog-workflow.md` created with comprehensive documentation
- [ ] `README.md` updated with new workflow entry
- [ ] All changes committed with descriptive commit message
- [ ] Branch pushed to remote
- [ ] Pull Request created
- [ ] Code review completed with all issues addressed

---

## Post-Implementation Testing

After the PR is merged, test the workflow:

### Test 1: Single App Repository

1. Create a test tag on a single-app repository
2. Trigger the gptchangelog workflow
3. Verify CHANGELOG.md and RELEASE_NOTES.md are generated
4. Verify GitHub Release is updated
5. Verify PR is created and merged

### Test 2: Monorepo (Helm Charts)

1. Make changes to one chart in the helm repository
2. Create a tag for that chart
3. Trigger the gptchangelog workflow with appropriate filter_paths
4. Verify only the changed chart gets a changelog
5. Verify the PR is created with correct app name

### Test 3: Slack Notifications

1. Configure SLACK_WEBHOOK_URL secret
2. Run the workflow
3. Verify Slack notification is received

---

**Plan created:** 2025-12-12
**Author:** Factory Planning Agent
