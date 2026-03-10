<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>slack-release</h1></td>
  </tr>
</table>

Composite action that sends a release notification to a Slack channel via webhook. Wraps [rtCamp/action-slack-notify](https://github.com/rtCamp/action-slack-notify).

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `webhook-url` | Slack webhook URL | Yes | — |
| `channel` | Slack channel name | Yes | — |
| `product-name` | Product name displayed in the notification title | Yes | — |
| `release-tag` | Release tag (e.g. `v1.2.3`) | Yes | — |
| `color` | Sidebar color for the Slack message | No | `#36a64f` |
| `icon-emoji` | Emoji icon for the bot | No | `:rocket:` |
| `dry-run` | Preview changes without sending the notification | No | `false` |

## Usage

### As a composite action (inline step)

```yaml
jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
      - uses: LerianStudio/github-actions-shared-workflows/src/notify/slack-release@v1.2.3
        with:
          webhook-url: ${{ secrets.SLACK_WEBHOOK_URL }}
          channel: "releases"
          product-name: "MyProduct"
          release-tag: "v1.0.0"
```

### As a reusable workflow (recommended)

```yaml
jobs:
  notify:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/release-notification.yml@v1.2.3
    with:
      product_name: "MyProduct"
      slack_channel: "releases"
    secrets:
      APP_ID: ${{ secrets.APP_ID }}
      APP_PRIVATE_KEY: ${{ secrets.APP_PRIVATE_KEY }}
      SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### Dry run (preview only)

```yaml
- uses: LerianStudio/github-actions-shared-workflows/src/notify/slack-release@develop
  with:
    webhook-url: ${{ secrets.SLACK_WEBHOOK_URL }}
    channel: "releases"
    product-name: "MyProduct"
    release-tag: "v1.0.0"
    dry-run: "true"
```

## Permissions required

No special permissions required beyond the webhook URL secret.
