<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>stale</h1></td>
  </tr>
</table>

> **Compatibility wrapper.** Prefer the dedicated [`stale-pr.yml`](./stale-pr.md) and [`stale-issue.yml`](./stale-issue.md) workflows for new adoptions. This entrypoint is kept so callers that adopted `stale.yml` in v1.26.4 continue to work; it forwards the combined inputs to the two split workflows in parallel jobs.

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `days_before_pr_stale` | Days of PR inactivity before applying the stale label | No | `30` |
| `days_before_pr_close` | Days after a PR is marked stale before it is closed | No | `14` |
| `days_before_issue_stale` | Days of issue inactivity before applying the stale label | No | `60` |
| `days_before_issue_close` | Days after an issue is marked stale before it is closed | No | `14` |
| `exempt_pr_labels` | Comma-separated labels exempting a PR from the stale scan | No | `no-stale,security,work-in-progress` |
| `exempt_issue_labels` | Comma-separated labels exempting an issue from the stale scan | No | `no-stale,security,pinned` |
| `operations_per_run` | Maximum API operations per run | No | `60` |
| `dry_run` | Preview changes without applying them | No | `false` |

## Usage

### Testing (against `@develop`)

```yaml
jobs:
  stale:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/stale.yml@develop
    with:
      dry_run: true
    secrets: inherit
```

### Production (pinned)

```yaml
jobs:
  stale:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/stale.yml@vX.Y.Z
    secrets: inherit
```

## Permissions required

```yaml
permissions:
  pull-requests: write
  issues: write
```
