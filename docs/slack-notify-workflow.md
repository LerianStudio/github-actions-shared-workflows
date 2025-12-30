# Slack Notify Workflow

Reusable workflow for sending Slack notifications from GitHub Actions. Designed to be called as a final step from other workflows to report success or failure status.

## Features

- **Rich formatting**: Repository name, workflow, failed jobs, author, branch, and commit info
- **Status-based colors**: Green for success, red for failure, gray for cancelled
- **Graceful degradation**: Skips silently if `SLACK_WEBHOOK_URL` is not configured
- **Custom messages**: Optional additional context in notifications
- **PR support**: Shows PR number and branch for pull request events

## Usage

### Basic Usage (from another workflow)

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Build
        run: make build

  notify:
    needs: [build]
    if: always()
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/slack-notify.yml@main
    with:
      status: ${{ needs.build.result }}
      workflow_name: "Build Pipeline"
    secrets: inherit
```

### With Failed Jobs Information

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - run: make lint

  test:
    runs-on: ubuntu-latest
    steps:
      - run: make test

  notify:
    needs: [lint, test]
    if: always()
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/slack-notify.yml@main
    with:
      status: ${{ needs.lint.result == 'failure' && 'failure' || needs.test.result }}
      workflow_name: "CI Pipeline"
      failed_jobs: ${{ needs.lint.result == 'failure' && 'Lint' || '' }}${{ needs.test.result == 'failure' && ', Test' || '' }}
    secrets: inherit
```

### With Custom Message

```yaml
notify:
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/slack-notify.yml@main
  with:
    status: "success"
    workflow_name: "Release"
    custom_message: "Version v1.2.3 has been released! 🎉"
    secrets: inherit
```

### Using secrets: inherit

```yaml
notify:
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/slack-notify.yml@main
  with:
    status: ${{ needs.build.result }}
    workflow_name: "Build"
  secrets: inherit
```

## Inputs

| Input | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `status` | string | Yes | - | Workflow status: `success`, `failure`, `cancelled` |
| `workflow_name` | string | Yes | - | Name of the calling workflow |
| `failed_jobs` | string | No | `''` | Comma-separated list of failed job names |
| `custom_message` | string | No | `''` | Optional custom message to include |
| `runner_type` | string | No | `firmino-lxc-runners` | GitHub runner type |

## Secrets

| Secret | Required | Description |
|--------|----------|-------------|
| `SLACK_WEBHOOK_URL` | No | Slack incoming webhook URL. If not provided, notification is skipped. |

## Notification Format

### Success Notification

```
✅ *Build Pipeline* succeeded in *my-repo*
👤 *Author:* octocat
📌 *Branch:* `feature/new-feature` | *Commit:* `abc1234`

🔗 View Workflow Run
```

### Failure Notification

```
❌ *Build Pipeline* failed in *my-repo*
💥 *Failed jobs:* Lint, Test
👤 *Author:* octocat
📌 *Branch:* `feature/new-feature` | *Commit:* `abc1234`

🔗 View Workflow Run
```

### Cancelled Notification

```
⚪ *Build Pipeline* was cancelled in *my-repo*
👤 *Author:* octocat
📌 *Branch:* `feature/new-feature` | *Commit:* `abc1234`

🔗 View Workflow Run
```

## Status Colors

| Status | Emoji | Color |
|--------|-------|-------|
| `success` | ✅ | Green |
| `failure` | ❌ | Red (danger) |
| `cancelled` | ⚪ | Gray |
| Other | ⚠️ | Yellow (warning) |

## Pull Request Events

For pull request events, the notification shows:
- PR number instead of branch name
- Head branch of the PR

## Setting Up Slack Webhook

1. Go to your Slack workspace settings
2. Navigate to **Apps** → **Incoming Webhooks**
3. Click **Add New Webhook to Workspace**
4. Select the channel for notifications
5. Copy the webhook URL
6. Add as `SLACK_WEBHOOK_URL` secret in GitHub repository or organization

## Graceful Degradation

If `SLACK_WEBHOOK_URL` is not configured:
- Workflow logs: "⚠️ SLACK_WEBHOOK_URL not configured - skipping notification"
- No error is raised
- Workflow completes successfully

This allows workflows to be used in repositories without Slack integration.

## Integration with Other Workflows

The slack-notify workflow is automatically integrated into:

- [Build Workflow](build-workflow.md)
- [Release Workflow](release-workflow.md)
- [Go PR Analysis](go-pr-analysis-workflow.md)
- [PR Validation](pr-validation-workflow.md)
- [PR Security Scan](pr-security-scan-workflow.md)

## Best Practices

1. **Always use `if: always()`**: Ensures notification runs even if previous jobs fail
2. **Include failed job names**: Helps quickly identify what went wrong
3. **Use `secrets: inherit`**: Simplifies secret management in calling workflows
4. **Set up at organization level**: Configure `SLACK_WEBHOOK_URL` as an org secret

## Troubleshooting

### Notification not sent

**Issue**: No Slack notification appears

**Solutions**:
1. Verify `SLACK_WEBHOOK_URL` secret is configured
2. Check workflow logs for "skipping notification" message
3. Ensure webhook URL is valid and channel exists

### Wrong status color

**Issue**: Notification shows wrong color

**Solution**: Ensure `status` input matches one of: `success`, `failure`, `cancelled`

### Missing job information

**Issue**: Failed jobs not shown in notification

**Solution**: Pass `failed_jobs` input with comma-separated job names

## Related Workflows

- [Build Workflow](build-workflow.md) - Uses slack-notify for build notifications
- [Release Workflow](release-workflow.md) - Uses slack-notify for release notifications

---

**Last Updated:** 2025-12-09
**Version:** 1.0.0
