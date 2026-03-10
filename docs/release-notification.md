<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>release-notification</h1></td>
  </tr>
</table>

Reusable workflow that sends release notifications to Discord and Slack. Fetches the latest release tag via GitHub CLI and dispatches to channel-specific composite actions.

## Architecture

```
release-notification.yml
    ├── src/notify/discord-release   (SethCohen/github-releases-to-discord)
    └── src/notify/slack-release     (rtCamp/action-slack-notify)
```

## Inputs

| Input | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `product_name` | `string` | Yes | — | Product name displayed in notifications |
| `slack_channel` | `string` | No | `""` | Slack channel name |
| `discord_color` | `string` | No | `2105893` | Discord embed color (decimal) |
| `discord_username` | `string` | No | `Release Changelog` | Bot username in Discord |
| `discord_content` | `string` | No | `""` | Discord message content (e.g. role mentions) |
| `skip_beta_discord` | `boolean` | No | `true` | Skip Discord notification for beta releases |
| `slack_color` | `string` | No | `#36a64f` | Sidebar color for Slack message |
| `slack_icon_emoji` | `string` | No | `:rocket:` | Emoji icon for Slack bot |
| `dry_run` | `boolean` | No | `false` | Preview changes without sending notifications |

## Secrets

| Secret | Required | Description |
|---|---|---|
| `APP_ID` | Yes | GitHub App ID for authentication |
| `APP_PRIVATE_KEY` | Yes | GitHub App private key |
| `DISCORD_WEBHOOK_URL` | No | Discord webhook URL (skipped if empty) |
| `SLACK_WEBHOOK_URL` | No | Slack webhook URL (skipped if empty) |

## Usage

### Basic (Discord + Slack)

```yaml
name: "Release Notifications"

on:
  release:
    types: [published]

jobs:
  notify:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/release-notification.yml@v1.2.3
    with:
      product_name: "Midaz"
      slack_channel: "lerian-product-release"
      discord_content: "<@&1346912737380274176>"
    secrets:
      APP_ID: ${{ secrets.LERIAN_STUDIO_MIDAZ_PUSH_BOT_APP_ID }}
      APP_PRIVATE_KEY: ${{ secrets.LERIAN_STUDIO_MIDAZ_PUSH_BOT_PRIVATE_KEY }}
      DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
      SLACK_WEBHOOK_URL: ${{ secrets.RELEASE_WEBHOOK_NOTIFICATION_URL }}
```

### Discord only

```yaml
jobs:
  notify:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/release-notification.yml@v1.2.3
    with:
      product_name: "MyProduct"
      discord_content: "<@&ROLE_ID>"
    secrets:
      APP_ID: ${{ secrets.APP_ID }}
      APP_PRIVATE_KEY: ${{ secrets.APP_PRIVATE_KEY }}
      DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
```

### Slack only

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

### Dry run (testing)

```yaml
jobs:
  notify:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/release-notification.yml@develop
    with:
      product_name: "MyProduct"
      slack_channel: "test-channel"
      dry_run: true
    secrets:
      APP_ID: ${{ secrets.APP_ID }}
      APP_PRIVATE_KEY: ${{ secrets.APP_PRIVATE_KEY }}
      DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
      SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

## Permissions required

```yaml
permissions:
  contents: read
```

The GitHub App token handles elevated API access for fetching release information.
