<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>stale</h1></td>
  </tr>
</table>

Reusable workflow that flags and closes stale PRs and issues. Wraps the [`stale`](../src/config/stale/README.md) composite action with Lerian defaults. Intended to run on a schedule or after PR merges to keep the backlog clean.

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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/stale.yml@v1.19.0
    secrets: inherit
```

## Permissions required

```yaml
permissions:
  pull-requests: write
  issues: write
```
