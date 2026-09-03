<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>release-notification</h1></td>
  </tr>
</table>

Reusable workflow that sends release notifications to Discord and Slack. Resolves the release tag from `release_tag`, then the release event, then the latest release via GitHub CLI, classifies the tag against the optional `RELEASE_NOTIFY_TAG_TYPES` allowlist, and dispatches to channel-specific composite actions.

The [release workflow](release-workflow.md) calls this workflow directly from its
`announce_release` job (Slack only), so most repositories do not need a standalone caller —
see [Release Announcement](release-workflow.md#release-announcement). A dedicated caller with
`on: release` is still required for Discord.

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
| `release_tag` | `string` | No | `""` | Release tag to announce. When empty, resolves from the release event and then from the latest release |
| `discord_color` | `string` | No | `2105893` | Discord embed color (decimal) |
| `discord_username` | `string` | No | `Release Changelog` | Bot username in Discord |
| `discord_content` | `string` | No | `""` | Discord message content (e.g. role mentions) |
| `skip_beta_discord` | `boolean` | No | `true` | Skip Discord notification for beta releases |
| `slack_color` | `string` | No | `#36a64f` | Sidebar color for Slack message |
| `slack_icon_emoji` | `string` | No | `:rocket:` | Emoji icon for Slack bot |
| `dry_run` | `boolean` | No | `false` | Preview changes without sending notifications |

## Tag granularity — `RELEASE_NOTIFY_TAG_TYPES`

By default every resolved tag is announced. To restrict which tags produce a
notification, define the **Actions variable `RELEASE_NOTIFY_TAG_TYPES`** with a
comma-separated allowlist of tag types:

```text
RELEASE_NOTIFY_TAG_TYPES = beta,rc,stable
```

The workflow classifies the resolved tag and announces it only when its type is
on the list. Values are case-insensitive and surrounding spaces are ignored, so
`beta, RC , Stable` is equivalent.

| Tag | Type |
|---|---|
| `v1.2.3` | `stable` |
| `v1.2.3-beta.4` | `beta` |
| `v1.2.3-rc.1` | `rc` |
| `v1.2.3-alpha.1` | `alpha` |
| `v1.2.3-canary.7` | `canary` |
| anything not matching semver (e.g. `nightly`) | `unknown` |

Any pre-release identifier becomes its own type, so the allowlist is open-ended —
`alpha`, `dev`, `canary` and `snapshot` all work without a workflow change.
Build metadata is ignored: `v1.2.3+build.9` is `stable`.

**Scope and precedence.** Set the variable once at the **organization** level for
the default policy, then override it on a **repository** that needs a different
granularity — repository variables take precedence over organization variables
natively in GitHub. The workflow reads `vars` in the context of the repository
that triggered the run, so a per-repo value applies without touching the caller
workflow. This also covers the announcement made by
[`release.yml`](release-workflow.md#release-announcement), which calls this
workflow internally.

Two behaviors worth knowing before setting the variable:

- **The allowlist is strict.** With `beta,rc,stable`, a `v1.2.3-alpha.1` release
  stops notifying — add `alpha` explicitly if you want it.
- **`skip_beta_discord` still applies, in AND.** It defaults to `true`, so
  listing `beta` makes Slack announce beta releases while Discord keeps skipping
  them. Pass `skip_beta_discord: false` in the caller to let Discord announce
  beta too.

Leave the variable undefined (or empty) to keep announcing every tag.

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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/release-notification.yml@tier-1
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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/release-notification.yml@tier-1
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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/release-notification.yml@tier-1
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
