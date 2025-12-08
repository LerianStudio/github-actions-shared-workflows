# Slack Notifications Implementation Plan

> **For Agents:** REQUIRED SUB-SKILL: Use ring-default:executing-plans to implement this plan task-by-task.

**Goal:** Add Slack notifications for workflow success/failure to all shared GitHub Actions workflows without requiring app repos to explicitly pass the webhook secret.

**Architecture:** Create a dedicated `slack-notify.yml` reusable workflow that accepts status and context as inputs. Each existing workflow will call this as a final job. The Slack webhook URL will be set as an organization-level secret and inherited via `secrets: inherit`.

**Tech Stack:** GitHub Actions, rtCamp/action-slack-notify@v2, YAML

**Global Prerequisites:**
- Environment: macOS/Linux with git
- Tools: Text editor, GitHub CLI (optional)
- Access: Write access to `LerianStudio/github-actions-shared-workflows` repository
- State: On `feature/go-workflows` branch with clean working tree
- Organization secret: `SLACK_WEBHOOK_URL` must be set at organization level

**Verification before starting:**
```bash
# Run ALL these commands and verify output:
cd /Users/ferr3ira/Documents/empresas/lerian-studio/projetos/github/modules/github-actions-shared-workflows
git branch --show-current  # Expected: feature/go-workflows
git status                 # Expected: clean working tree (no uncommitted changes)
ls .github/workflows/      # Expected: build.yml, go-pr-analysis.yml, pr-validation.yml, etc.
```

---

## Overview

### What We're Building

1. **`slack-notify.yml`** - A new reusable workflow that:
   - Accepts workflow status, name, and optional custom message
   - Sends formatted Slack notifications with repo name, commit info, and links
   - Gracefully skips if `SLACK_WEBHOOK_URL` is not available

2. **Updates to existing workflows** - Add a final notification job to:
   - `build.yml` - Docker image builds
   - `go-pr-analysis.yml` - Go PR analysis
   - `pr-validation.yml` - PR validation
   - `pr-security-scan.yml` - Security scanning
   - `release.yml` - Semantic release
   - `gitops-update.yml` - GitOps updates
   - `api-dog-e2e-tests.yml` - E2E tests
   - `go-release.yml` - Go release

### Key Design Decisions

1. **Separate reusable workflow** - Easier to maintain, update, and test
2. **Optional notifications** - Check if secret exists before sending
3. **Rich messages** - Include context (repo, workflow, status, link)
4. **Consistent format** - Same message structure across all workflows
5. **No app repo changes required** - App repos just need `secrets: inherit`

---

## Task 1: Create `slack-notify.yml` Reusable Workflow

**Files:**
- Create: `.github/workflows/slack-notify.yml`

**Prerequisites:**
- On `feature/go-workflows` branch
- Repository checked out

**Step 1: Create the Slack notification workflow file**

Create file `.github/workflows/slack-notify.yml` with the following content:

```yaml
name: "Slack Notification"

# Reusable workflow for sending Slack notifications
# Designed to be called from other workflows as a final notification step
#
# Features:
# - Rich formatting with repo, workflow, status, and link
# - Gracefully skips if SLACK_WEBHOOK_URL secret is not available
# - Supports custom messages and emoji customization

on:
  workflow_call:
    inputs:
      status:
        description: 'Workflow status (success, failure, cancelled)'
        type: string
        required: true
      workflow_name:
        description: 'Name of the calling workflow'
        type: string
        required: true
      custom_message:
        description: 'Optional custom message to include'
        type: string
        required: false
        default: ''
      include_commit_info:
        description: 'Include commit SHA and author in message'
        type: boolean
        default: true
      runner_type:
        description: 'GitHub runner type to use'
        type: string
        default: 'ubuntu-latest'
      notify_on_success:
        description: 'Send notification on success'
        type: boolean
        default: true
      notify_on_failure:
        description: 'Send notification on failure'
        type: boolean
        default: true
      notify_on_cancelled:
        description: 'Send notification on cancelled'
        type: boolean
        default: false
    secrets:
      slack_webhook_url:
        description: 'Slack webhook URL for notifications'
        required: false

jobs:
  notify:
    name: Send Notification
    runs-on: ${{ inputs.runner_type }}
    steps:
      - name: Check if Slack webhook is configured
        id: check_webhook
        run: |
          if [ -z "${{ secrets.slack_webhook_url }}" ]; then
            echo "skip=true" >> $GITHUB_OUTPUT
            echo "⚠️ SLACK_WEBHOOK_URL not configured - skipping notification"
          else
            echo "skip=false" >> $GITHUB_OUTPUT
            echo "✅ Slack webhook configured"
          fi

      - name: Determine notification settings
        if: steps.check_webhook.outputs.skip != 'true'
        id: settings
        run: |
          STATUS="${{ inputs.status }}"
          
          # Check if we should notify for this status
          SHOULD_NOTIFY="false"
          if [ "$STATUS" = "success" ] && [ "${{ inputs.notify_on_success }}" = "true" ]; then
            SHOULD_NOTIFY="true"
          elif [ "$STATUS" = "failure" ] && [ "${{ inputs.notify_on_failure }}" = "true" ]; then
            SHOULD_NOTIFY="true"
          elif [ "$STATUS" = "cancelled" ] && [ "${{ inputs.notify_on_cancelled }}" = "true" ]; then
            SHOULD_NOTIFY="true"
          fi
          echo "should_notify=$SHOULD_NOTIFY" >> $GITHUB_OUTPUT
          
          # Set color based on status
          case "$STATUS" in
            success)
              COLOR="good"
              EMOJI="✅"
              STATUS_TEXT="succeeded"
              ;;
            failure)
              COLOR="danger"
              EMOJI="❌"
              STATUS_TEXT="failed"
              ;;
            cancelled)
              COLOR="#808080"
              EMOJI="⚪"
              STATUS_TEXT="was cancelled"
              ;;
            *)
              COLOR="warning"
              EMOJI="⚠️"
              STATUS_TEXT="completed with status: $STATUS"
              ;;
          esac
          
          echo "color=$COLOR" >> $GITHUB_OUTPUT
          echo "emoji=$EMOJI" >> $GITHUB_OUTPUT
          echo "status_text=$STATUS_TEXT" >> $GITHUB_OUTPUT

      - name: Build notification message
        if: steps.check_webhook.outputs.skip != 'true' && steps.settings.outputs.should_notify == 'true'
        id: message
        run: |
          REPO="${{ github.repository }}"
          REPO_NAME="${REPO##*/}"
          WORKFLOW="${{ inputs.workflow_name }}"
          STATUS_TEXT="${{ steps.settings.outputs.status_text }}"
          EMOJI="${{ steps.settings.outputs.emoji }}"
          RUN_URL="${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
          
          # Build base message
          MESSAGE="$EMOJI *$WORKFLOW* $STATUS_TEXT in *$REPO_NAME*"
          
          # Add custom message if provided
          if [ -n "${{ inputs.custom_message }}" ]; then
            MESSAGE="$MESSAGE\n\n${{ inputs.custom_message }}"
          fi
          
          # Add commit info if enabled
          if [ "${{ inputs.include_commit_info }}" = "true" ]; then
            COMMIT_SHA="${{ github.sha }}"
            SHORT_SHA="${COMMIT_SHA:0:7}"
            ACTOR="${{ github.actor }}"
            
            # Handle different event types for ref info
            if [ "${{ github.event_name }}" = "pull_request" ]; then
              REF="PR #${{ github.event.pull_request.number }}"
              BRANCH="${{ github.head_ref }}"
            else
              REF="${{ github.ref_name }}"
              BRANCH="$REF"
            fi
            
            MESSAGE="$MESSAGE\n\n📌 *Ref:* \`$REF\` | *Commit:* \`$SHORT_SHA\` | *By:* $ACTOR"
          fi
          
          # Add link to workflow run
          MESSAGE="$MESSAGE\n\n<$RUN_URL|View Workflow Run>"
          
          # Escape for JSON (handle newlines)
          MESSAGE_ESCAPED=$(echo "$MESSAGE" | sed 's/\\n/\n/g')
          
          echo "message<<EOF" >> $GITHUB_OUTPUT
          echo "$MESSAGE_ESCAPED" >> $GITHUB_OUTPUT
          echo "EOF" >> $GITHUB_OUTPUT

      - name: Send Slack notification
        if: steps.check_webhook.outputs.skip != 'true' && steps.settings.outputs.should_notify == 'true'
        uses: rtCamp/action-slack-notify@v2
        env:
          SLACK_WEBHOOK: ${{ secrets.slack_webhook_url }}
          SLACK_COLOR: ${{ steps.settings.outputs.color }}
          SLACK_USERNAME: GitHub Actions
          SLACK_ICON: https://github.githubassets.com/assets/GitHub-Mark-ea2971cee799.png
          SLACK_TITLE: ${{ inputs.workflow_name }}
          SLACK_MESSAGE: ${{ steps.message.outputs.message }}
          SLACK_FOOTER: ${{ github.repository }}
          MSG_MINIMAL: true

      - name: Log notification skipped
        if: steps.check_webhook.outputs.skip == 'true' || steps.settings.outputs.should_notify != 'true'
        run: |
          if [ "${{ steps.check_webhook.outputs.skip }}" = "true" ]; then
            echo "📭 Notification skipped: SLACK_WEBHOOK_URL not configured"
          else
            echo "📭 Notification skipped: notify_on_${{ inputs.status }} is disabled"
          fi
```

**Step 2: Verify file was created correctly**

Run: `cat .github/workflows/slack-notify.yml | head -50`

**Expected output:**
```
name: "Slack Notification"

# Reusable workflow for sending Slack notifications
# Designed to be called from other workflows as a final notification step
```

**Step 3: Commit the new workflow**

```bash
git add .github/workflows/slack-notify.yml
git commit -m "feat(slack): add reusable Slack notification workflow

- Accepts status, workflow name, and optional custom message
- Gracefully skips if SLACK_WEBHOOK_URL secret not available
- Rich formatting with repo, commit, and link info
- Configurable notifications per status type"
```

**If Task Fails:**

1. **File not created:**
   - Check: `ls -la .github/workflows/`
   - Fix: Ensure you're in repository root
   - Rollback: N/A (no changes yet)

2. **Commit fails:**
   - Run: `git status` (check what's staged)
   - Rollback: `git checkout -- .github/workflows/slack-notify.yml`

3. **Can't recover:**
   - Document: What failed and why
   - Stop: Return to human partner

---

## Task 2: Update `build.yml` with Slack Notification

**Files:**
- Modify: `.github/workflows/build.yml` (add at end of file)

**Prerequisites:**
- Task 1 completed
- `slack-notify.yml` exists in `.github/workflows/`

**Step 1: Add notification job to build.yml**

Append the following job at the end of `.github/workflows/build.yml` (after the `build` job):

```yaml

  # Slack notification for build status
  notify:
    name: Notify
    needs: [prepare, build]
    if: always() && needs.prepare.outputs.has_builds == 'true'
    uses: ./.github/workflows/slack-notify.yml
    with:
      status: ${{ needs.build.result }}
      workflow_name: "Docker Build & Push"
      custom_message: "🐳 Built images for ${{ github.ref_name }}"
      notify_on_success: true
      notify_on_failure: true
    secrets:
      slack_webhook_url: ${{ secrets.SLACK_WEBHOOK_URL }}
```

**Step 2: Verify the modification**

Run: `tail -20 .github/workflows/build.yml`

**Expected output:** Should show the new `notify` job with proper indentation.

**Step 3: Commit the change**

```bash
git add .github/workflows/build.yml
git commit -m "feat(build): add Slack notification on completion

- Notifies on success and failure
- Includes build tag in message
- Gracefully skips if webhook not configured"
```

**If Task Fails:**

1. **YAML syntax error:**
   - Check: Indentation must match existing jobs
   - Fix: Ensure 2-space indentation, job at same level as `build`
   - Rollback: `git checkout -- .github/workflows/build.yml`

2. **Job dependency error:**
   - Check: `needs: [prepare, build]` - both jobs must exist
   - Fix: Verify job names in file

3. **Can't recover:**
   - Document: What failed and why
   - Stop: Return to human partner

---

## Task 3: Update `go-pr-analysis.yml` with Slack Notification

**Files:**
- Modify: `.github/workflows/go-pr-analysis.yml` (add at end of file)

**Prerequisites:**
- Task 1 completed

**Step 1: Add notification job to go-pr-analysis.yml**

Append the following job at the end of `.github/workflows/go-pr-analysis.yml` (after the `no-changes` job):

```yaml

  # Slack notification for PR analysis status
  notify:
    name: Notify
    needs: [detect-changes, lint, security, tests, coverage, build]
    if: always() && needs.detect-changes.outputs.has_changes == 'true'
    uses: ./.github/workflows/slack-notify.yml
    with:
      status: ${{ (needs.lint.result == 'failure' || needs.security.result == 'failure' || needs.tests.result == 'failure' || needs.build.result == 'failure') && 'failure' || 'success' }}
      workflow_name: "Go PR Analysis"
      custom_message: "🔍 PR analysis for ${{ github.head_ref || github.ref_name }}"
      notify_on_success: false
      notify_on_failure: true
    secrets:
      slack_webhook_url: ${{ secrets.SLACK_WEBHOOK_URL }}
```

**Step 2: Verify the modification**

Run: `tail -20 .github/workflows/go-pr-analysis.yml`

**Expected output:** Should show the new `notify` job.

**Step 3: Commit the change**

```bash
git add .github/workflows/go-pr-analysis.yml
git commit -m "feat(go-pr-analysis): add Slack notification on failure

- Only notifies on failure (PR analysis failures need attention)
- Aggregates status from lint, security, tests, and build jobs"
```

**If Task Fails:**

1. **YAML syntax error:**
   - Check: Proper indentation and YAML syntax
   - Rollback: `git checkout -- .github/workflows/go-pr-analysis.yml`

2. **Job reference error:**
   - Check: All job names in `needs` array exist
   - Note: Some jobs may be skipped based on inputs

---

## Task 4: Update `pr-validation.yml` with Slack Notification

**Files:**
- Modify: `.github/workflows/pr-validation.yml` (add at end of file)

**Prerequisites:**
- Task 1 completed

**Step 1: Add notification job to pr-validation.yml**

Append the following job at the end of `.github/workflows/pr-validation.yml` (after the `pr-checks-summary` job):

```yaml

  # Slack notification for PR validation status
  notify:
    name: Notify
    needs: [pr-title, pr-size, pr-description]
    if: always()
    uses: ./.github/workflows/slack-notify.yml
    with:
      status: ${{ needs.pr-title.result == 'failure' && 'failure' || 'success' }}
      workflow_name: "PR Validation"
      notify_on_success: false
      notify_on_failure: true
    secrets:
      slack_webhook_url: ${{ secrets.SLACK_WEBHOOK_URL }}
```

**Step 2: Verify the modification**

Run: `tail -15 .github/workflows/pr-validation.yml`

**Step 3: Commit the change**

```bash
git add .github/workflows/pr-validation.yml
git commit -m "feat(pr-validation): add Slack notification on failure

- Only notifies when PR title validation fails
- Helps catch invalid PR titles early"
```

**If Task Fails:**

1. **YAML syntax error:**
   - Rollback: `git checkout -- .github/workflows/pr-validation.yml`

---

## Task 5: Update `pr-security-scan.yml` with Slack Notification

**Files:**
- Modify: `.github/workflows/pr-security-scan.yml` (add at end of file)

**Prerequisites:**
- Task 1 completed

**Step 1: Add notification job to pr-security-scan.yml**

Append the following job at the end of `.github/workflows/pr-security-scan.yml` (after the `security_scan` job):

```yaml

  # Slack notification for security scan status
  notify:
    name: Notify
    needs: [prepare_matrix, security_scan]
    if: always() && needs.prepare_matrix.outputs.matrix != '[]'
    uses: ./.github/workflows/slack-notify.yml
    with:
      status: ${{ needs.security_scan.result }}
      workflow_name: "PR Security Scan"
      custom_message: "🔒 Security scan completed"
      notify_on_success: false
      notify_on_failure: true
    secrets:
      slack_webhook_url: ${{ secrets.SLACK_WEBHOOK_URL }}
```

**Step 2: Verify the modification**

Run: `tail -15 .github/workflows/pr-security-scan.yml`

**Step 3: Commit the change**

```bash
git add .github/workflows/pr-security-scan.yml
git commit -m "feat(pr-security-scan): add Slack notification on failure

- Notifies when security vulnerabilities are found
- Critical for maintaining security awareness"
```

---

## Task 6: Update `release.yml` with Slack Notification

**Files:**
- Modify: `.github/workflows/release.yml` (add at end of file)

**Prerequisites:**
- Task 1 completed

**Step 1: Add notification job to release.yml**

Append the following job at the end of `.github/workflows/release.yml` (after the `publish_release` job):

```yaml

  # Slack notification for release status
  notify:
    name: Notify
    needs: [prepare, publish_release]
    if: always() && needs.prepare.outputs.has_changes == 'true'
    uses: ./.github/workflows/slack-notify.yml
    with:
      status: ${{ needs.publish_release.result }}
      workflow_name: "Release"
      custom_message: "🚀 Release workflow completed for ${{ github.ref_name }}"
      notify_on_success: true
      notify_on_failure: true
    secrets:
      slack_webhook_url: ${{ secrets.SLACK_WEBHOOK_URL }}
```

**Step 2: Verify the modification**

Run: `tail -15 .github/workflows/release.yml`

**Step 3: Commit the change**

```bash
git add .github/workflows/release.yml
git commit -m "feat(release): add Slack notification on completion

- Notifies on both success and failure
- Release events are important to track"
```

---

## Task 7: Update `gitops-update.yml` with Slack Notification

**Files:**
- Modify: `.github/workflows/gitops-update.yml` (add at end of file)

**Prerequisites:**
- Task 1 completed

**Step 1: Add notification job to gitops-update.yml**

Append the following job at the end of `.github/workflows/gitops-update.yml` (after the `update_gitops` job):

```yaml

  # Slack notification for GitOps update status
  notify:
    name: Notify
    needs: [update_gitops]
    if: always()
    uses: ./.github/workflows/slack-notify.yml
    with:
      status: ${{ needs.update_gitops.result }}
      workflow_name: "GitOps Update"
      custom_message: "🔄 GitOps repository updated for ${{ github.ref_name }}"
      notify_on_success: true
      notify_on_failure: true
    secrets:
      slack_webhook_url: ${{ secrets.SLACK_WEBHOOK_URL }}
```

**Step 2: Verify the modification**

Run: `tail -15 .github/workflows/gitops-update.yml`

**Step 3: Commit the change**

```bash
git add .github/workflows/gitops-update.yml
git commit -m "feat(gitops-update): add Slack notification on completion

- Notifies when GitOps repository is updated
- Helps track deployment pipeline progress"
```

---

## Task 8: Update `api-dog-e2e-tests.yml` with Slack Notification

**Files:**
- Modify: `.github/workflows/api-dog-e2e-tests.yml` (add at end of file)

**Prerequisites:**
- Task 1 completed

**Step 1: Add notification job to api-dog-e2e-tests.yml**

Append the following job at the end of `.github/workflows/api-dog-e2e-tests.yml` (after the `api-dog-e2e-tests` job):

```yaml

  # Slack notification for E2E test status
  notify:
    name: Notify
    needs: [api-dog-e2e-tests]
    if: always()
    uses: ./.github/workflows/slack-notify.yml
    with:
      status: ${{ needs.api-dog-e2e-tests.result }}
      workflow_name: "API E2E Tests"
      custom_message: "🧪 E2E tests completed for ${{ github.ref_name }}"
      notify_on_success: true
      notify_on_failure: true
    secrets:
      slack_webhook_url: ${{ secrets.SLACK_WEBHOOK_URL }}
```

**Step 2: Verify the modification**

Run: `tail -15 .github/workflows/api-dog-e2e-tests.yml`

**Step 3: Commit the change**

```bash
git add .github/workflows/api-dog-e2e-tests.yml
git commit -m "feat(api-dog-e2e-tests): add Slack notification on completion

- Notifies on E2E test success and failure
- Critical for deployment pipeline visibility"
```

---

## Task 9: Update `go-release.yml` with Slack Notification

**Files:**
- Modify: `.github/workflows/go-release.yml` (add at end of file)

**Prerequisites:**
- Task 1 completed

**Step 1: Add notification job to go-release.yml**

Append the following job at the end of `.github/workflows/go-release.yml` (after the `notify` job - rename existing to avoid conflict):

The existing `notify` job in `go-release.yml` is for general notifications (placeholder). Replace it with Slack notification or add alongside. Since the existing notify job is a placeholder, we'll add a separate `slack_notify` job:

```yaml

  # Slack notification for Go release status
  slack_notify:
    name: Slack Notify
    needs: [release, homebrew, docker]
    if: always() && startsWith(github.ref, 'refs/tags/v')
    uses: ./.github/workflows/slack-notify.yml
    with:
      status: ${{ needs.release.result }}
      workflow_name: "Go Release"
      custom_message: "📦 Go release ${{ github.ref_name }} completed"
      notify_on_success: true
      notify_on_failure: true
    secrets:
      slack_webhook_url: ${{ secrets.SLACK_WEBHOOK_URL }}
```

**Step 2: Verify the modification**

Run: `tail -15 .github/workflows/go-release.yml`

**Step 3: Commit the change**

```bash
git add .github/workflows/go-release.yml
git commit -m "feat(go-release): add Slack notification on completion

- Notifies on Go release success and failure
- Tracks binary release status"
```

---

## Task 10: Create Documentation for App Repos

**Files:**
- Create: `docs/slack-notifications.md`

**Prerequisites:**
- Tasks 1-9 completed

**Step 1: Create documentation file**

Create file `docs/slack-notifications.md`:

```markdown
# Slack Notifications

All shared workflows support optional Slack notifications for workflow completion status.

## Setup

### 1. Organization Secret (Admin)

Set the `SLACK_WEBHOOK_URL` secret at the **organization level**:

1. Go to Organization Settings → Secrets and variables → Actions
2. Create a new organization secret named `SLACK_WEBHOOK_URL`
3. Paste your Slack webhook URL
4. Set repository access to "All repositories" or select specific repos

### 2. App Repository Configuration

To enable Slack notifications in your app repository, use `secrets: inherit` when calling shared workflows:

**Before (explicit secrets):**
```yaml
jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/build.yml@main
    with:
      enable_dockerhub: true
    secrets:
      docker_username: ${{ secrets.DOCKER_USERNAME }}
      docker_password: ${{ secrets.DOCKER_PASSWORD }}
```

**After (with inherit):**
```yaml
jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/build.yml@main
    with:
      enable_dockerhub: true
    secrets: inherit
```

The `secrets: inherit` directive passes ALL organization/repository secrets to the reusable workflow, including `SLACK_WEBHOOK_URL`.

## Notification Behavior

| Workflow | Success | Failure | Custom Message |
|----------|---------|---------|----------------|
| build.yml | ✅ | ✅ | Build tag info |
| go-pr-analysis.yml | ❌ | ✅ | PR branch info |
| pr-validation.yml | ❌ | ✅ | - |
| pr-security-scan.yml | ❌ | ✅ | - |
| release.yml | ✅ | ✅ | Release tag |
| gitops-update.yml | ✅ | ✅ | Deployment info |
| api-dog-e2e-tests.yml | ✅ | ✅ | Test results |
| go-release.yml | ✅ | ✅ | Release version |

## Graceful Degradation

If `SLACK_WEBHOOK_URL` is not configured:
- Workflows run normally without notifications
- No errors are thrown
- A log message indicates notification was skipped

## Message Format

Notifications include:
- ✅/❌ Workflow status icon
- Workflow name
- Repository name
- Commit SHA and author
- Branch/PR reference
- Link to workflow run

Example:
```
✅ Docker Build & Push succeeded in midaz
🐳 Built images for v1.2.3

📌 Ref: v1.2.3 | Commit: abc1234 | By: developer

View Workflow Run
```

## Creating a Slack Webhook

1. Go to [Slack API](https://api.slack.com/apps)
2. Create a new app or select existing
3. Enable "Incoming Webhooks"
4. Add a webhook to your desired channel
5. Copy the webhook URL

## Troubleshooting

**Notifications not appearing:**
1. Verify `SLACK_WEBHOOK_URL` is set at org level
2. Check workflow logs for "SLACK_WEBHOOK_URL not configured"
3. Ensure app repo uses `secrets: inherit`

**Wrong channel:**
- The webhook URL is tied to a specific channel
- Create different webhooks for different channels if needed
```

**Step 2: Commit the documentation**

```bash
git add docs/slack-notifications.md
git commit -m "docs: add Slack notifications setup guide

- Documents organization secret setup
- Shows app repo configuration with secrets: inherit
- Explains notification behavior per workflow
- Includes troubleshooting guide"
```

---

## Task 11: Update Repository README

**Files:**
- Modify: `README.md` (add Slack notifications section)

**Prerequisites:**
- Tasks 1-10 completed

**Step 1: Add Slack notifications section to README**

Add the following section to `README.md` after the workflows list section:

```markdown
## Slack Notifications

All workflows support optional Slack notifications. To enable:

1. **Set organization secret:** Add `SLACK_WEBHOOK_URL` at the organization level
2. **Use `secrets: inherit`:** In your app workflows when calling shared workflows

```yaml
jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/build.yml@main
    secrets: inherit  # Automatically passes SLACK_WEBHOOK_URL
```

See [docs/slack-notifications.md](docs/slack-notifications.md) for detailed setup instructions.
```

**Step 2: Commit the README update**

```bash
git add README.md
git commit -m "docs(readme): add Slack notifications section"
```

---

## Task 12: Final Verification

**Prerequisites:**
- All previous tasks completed

**Step 1: Verify all files are committed**

Run: `git status`

**Expected output:**
```
On branch feature/go-workflows
nothing to commit, working tree clean
```

**Step 2: Verify all workflow files have notify jobs**

Run: `grep -l "slack-notify.yml" .github/workflows/*.yml`

**Expected output:**
```
.github/workflows/api-dog-e2e-tests.yml
.github/workflows/build.yml
.github/workflows/gitops-update.yml
.github/workflows/go-pr-analysis.yml
.github/workflows/go-release.yml
.github/workflows/pr-security-scan.yml
.github/workflows/pr-validation.yml
.github/workflows/release.yml
```

**Step 3: Verify slack-notify.yml exists**

Run: `ls -la .github/workflows/slack-notify.yml`

**Expected output:**
```
-rw-r--r--  1 user  staff  XXXX date .github/workflows/slack-notify.yml
```

**Step 4: Validate YAML syntax for all modified files**

Run: `for f in .github/workflows/*.yml; do echo "Checking $f"; python3 -c "import yaml; yaml.safe_load(open('$f'))" && echo "✅ Valid" || echo "❌ Invalid"; done`

**Expected output:** All files should show "✅ Valid"

**Step 5: Review git log**

Run: `git log --oneline -15`

**Expected output:** Should show commits for each task.

---

## App Repository Migration Guide

After merging this branch, app repositories need to update their workflow calls to use `secrets: inherit`.

### Example Migration for Fetcher

**File:** `.github/workflows/build.yml` in fetcher repo

**Before:**
```yaml
jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/build.yml@feature/go-workflows
    with:
      enable_dockerhub: true
      enable_ghcr: true
    secrets:
      docker_username: ${{ secrets.DOCKER_USERNAME }}
      docker_password: ${{ secrets.DOCKER_PASSWORD }}
      ghcr_token: ${{ secrets.MANAGE_TOKEN }}
```

**After:**
```yaml
jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/build.yml@feature/go-workflows
    with:
      enable_dockerhub: true
      enable_ghcr: true
    secrets: inherit
```

### Benefits of `secrets: inherit`

1. **Simpler configuration** - No need to list each secret
2. **Automatic Slack notifications** - Works without changes when webhook is configured
3. **Future-proof** - New secrets added to shared workflows work automatically
4. **Less maintenance** - No need to update app repos when shared workflows change secrets

---

## Rollback Instructions

If issues arise after deployment:

### Rollback Single Workflow

```bash
# Revert specific workflow to previous version
git checkout HEAD~N -- .github/workflows/<workflow-name>.yml
git commit -m "revert: rollback <workflow-name> Slack notification"
```

### Rollback All Changes

```bash
# Revert all Slack notification changes
git revert --no-commit HEAD~11..HEAD
git commit -m "revert: rollback Slack notification implementation"
```

### Disable Notifications Without Rollback

Simply remove the `SLACK_WEBHOOK_URL` organization secret. All workflows will continue to run normally, just without notifications.

---

## Checklist

- [ ] Task 1: Created `slack-notify.yml`
- [ ] Task 2: Updated `build.yml`
- [ ] Task 3: Updated `go-pr-analysis.yml`
- [ ] Task 4: Updated `pr-validation.yml`
- [ ] Task 5: Updated `pr-security-scan.yml`
- [ ] Task 6: Updated `release.yml`
- [ ] Task 7: Updated `gitops-update.yml`
- [ ] Task 8: Updated `api-dog-e2e-tests.yml`
- [ ] Task 9: Updated `go-release.yml`
- [ ] Task 10: Created documentation
- [ ] Task 11: Updated README
- [ ] Task 12: Final verification passed
- [ ] Organization secret `SLACK_WEBHOOK_URL` configured
- [ ] App repos updated to use `secrets: inherit`
