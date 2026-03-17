<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>slack-notify</h1></td>
  </tr>
</table>

Composite action that sends a workflow status notification to Slack with rich formatting. Includes repo name, workflow name, failed jobs, author, branch, commit, and a link to the workflow run. Gracefully skips if the webhook URL is empty.

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `webhook-url` | Slack webhook URL for notifications | Yes | — |
| `status` | Workflow status (`success`, `failure`, `cancelled`) | Yes | — |
| `workflow-name` | Name of the calling workflow | Yes | — |
| `failed-jobs` | Comma-separated list of failed job names | No | `''` |
| `custom-message` | Optional custom message to include | No | `''` |

## Usage

### As a composite step (notification job)

```yaml
jobs:
  build:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - name: Build
        run: make build

  notify:
    needs: build
    if: always()
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - name: Slack Notification
        uses: LerianStudio/github-actions-shared-workflows/src/notify/slack-notify@develop
        with:
          webhook-url: ${{ secrets.SLACK_WEBHOOK_URL }}
          status: ${{ needs.build.result }}
          workflow-name: 'Build'
          failed-jobs: ${{ needs.build.result == 'failure' && 'Build' || '' }}
```

### Production usage

```yaml
- uses: LerianStudio/github-actions-shared-workflows/src/notify/slack-notify@v1.0.0
  with:
    webhook-url: ${{ secrets.SLACK_WEBHOOK_URL }}
    status: ${{ needs.build.result }}
    workflow-name: 'My Workflow'
```

## Permissions required

No special permissions required — notification is sent via webhook.
