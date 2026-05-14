<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>helm-release-notification</h1></td>
  </tr>
</table>

Reusable workflow for sending Slack notifications after Helm chart releases. Parses a version table from the repository README and sends a rich Slack message with native table blocks, action buttons, and optional team mentions.

## Inputs

| Input | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `chart_name` | `string` | **Yes** | — | Name of the Helm chart (e.g., `midaz-helm`) |
| `chart_path` | `string` | **Yes** | — | Path to the chart directory (e.g., `charts/midaz`) |
| `runner_type` | `string` | No | `ubuntu-latest` | Runner to use |
| `slack_color` | `string` | No | `#36a64f` | Sidebar color for the Slack message |
| `oci_registry` | `string` | No | `""` | OCI registry for chart packages |
| `dry_run` | `boolean` | No | `false` | Preview notification without sending |

## Secrets

| Secret | Required | Description |
|---|---|---|
| `SLACK_BOT_TOKEN` | **Yes** | Slack Bot OAuth Token (`xoxb-...`) |
| `SLACK_CHANNEL` | **Yes** | Slack channel ID for notifications |
| `SLACK_MENTION_GROUP` | No | Slack user group ID to mention in footer |

## Usage

### Basic usage (from a release pipeline)

```yaml
jobs:
  notify:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/helm-release-notification.yml@develop
    with:
      chart_name: "midaz-helm"
      chart_path: "charts/midaz"
    secrets:
      SLACK_BOT_TOKEN: ${{ secrets.SLACK_BOT_TOKEN_HELM }}
      SLACK_CHANNEL: ${{ secrets.SLACK_CHANNEL_DEVOPS }}
      SLACK_MENTION_GROUP: ${{ secrets.SLACK_GROUP_TECH_SUPPORT }}
```

### Dry run (preview only)

```yaml
jobs:
  notify:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/helm-release-notification.yml@develop
    with:
      chart_name: "midaz-helm"
      chart_path: "charts/midaz"
      dry_run: true
    secrets:
      SLACK_BOT_TOKEN: ${{ secrets.SLACK_BOT_TOKEN_HELM }}
      SLACK_CHANNEL: ${{ secrets.SLACK_CHANNEL_DEVOPS }}
```

### Via wrapper workflow (recommended for existing repos)

Keep a thin wrapper in your repo to avoid changing callers:

```yaml
# .github/workflows/release-notification.yml
name: Release Notification

on:
  workflow_call:
    inputs:
      chart_name:
        required: true
        type: string
      chart_path:
        required: true
        type: string
    secrets:
      SLACK_BOT_TOKEN_HELM:
        required: true
      SLACK_CHANNEL_DEVOPS:
        required: true
      SLACK_GROUP_TECH_SUPPORT:
        required: false

jobs:
  notify:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/helm-release-notification.yml@develop
    with:
      chart_name: ${{ inputs.chart_name }}
      chart_path: ${{ inputs.chart_path }}
    secrets:
      SLACK_BOT_TOKEN: ${{ secrets.SLACK_BOT_TOKEN_HELM }}
      SLACK_CHANNEL: ${{ secrets.SLACK_CHANNEL_DEVOPS }}
      SLACK_MENTION_GROUP: ${{ secrets.SLACK_GROUP_TECH_SUPPORT }}
```

## README format

The workflow expects a version table in the repository `README.md` with this structure:

```markdown
### Midaz Helm Chart

| Chart Version | Component A | Component B |
|---|---|---|
| `1.2.0` | `0.5.0` | `0.3.1` |
```

The chart name is matched case-insensitively against `### <heading>` sections.

## Permissions

```yaml
permissions:
  contents: read
```

## Slack message

The notification includes:
- Header with chart name and release emoji
- Native table block with component versions from README
- Action buttons: View Release, View Versions (README), View Commit
- Footer with timestamp, workflow link, and optional team mention
