<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>discord-release</h1></td>
  </tr>
</table>

Composite action that sends a release notification to a Discord channel via webhook. Wraps [SethCohen/github-releases-to-discord](https://github.com/SethCohen/github-releases-to-discord).

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `webhook-url` | Discord webhook URL | Yes | — |
| `release-tag` | Release tag (e.g. `v1.2.3` or `v1.0.0-beta.1`) | Yes | — |
| `color` | Embed color (decimal) | No | `2105893` |
| `username` | Bot username displayed in Discord | No | `Release Changelog` |
| `content` | Message content (e.g. role mentions) | No | `""` |
| `footer-timestamp` | Show timestamp in embed footer | No | `true` |
| `skip-beta` | Skip notification for beta releases | No | `true` |
| `dry-run` | Preview changes without sending the notification | No | `false` |

## Usage

### As a composite action (inline step)

```yaml
jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: LerianStudio/github-actions-shared-workflows/src/notify/discord-release@v1.2.3
        with:
          webhook-url: ${{ secrets.DISCORD_WEBHOOK_URL }}
          release-tag: ${{ github.event.release.tag_name }}
          content: "<@&1234567890>"
```

### As a reusable workflow (recommended)

```yaml
jobs:
  notify:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/release-notification.yml@v1.2.3
    with:
      product_name: "MyProduct"
      discord_content: "<@&1234567890>"
    secrets:
      APP_ID: ${{ secrets.APP_ID }}
      APP_PRIVATE_KEY: ${{ secrets.APP_PRIVATE_KEY }}
      DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
```

### Dry run (preview only)

```yaml
- uses: LerianStudio/github-actions-shared-workflows/src/notify/discord-release@develop
  with:
    webhook-url: ${{ secrets.DISCORD_WEBHOOK_URL }}
    release-tag: ${{ github.event.release.tag_name }}
    dry-run: "true"
```

## Permissions required

No special permissions required beyond the webhook URL secret.
