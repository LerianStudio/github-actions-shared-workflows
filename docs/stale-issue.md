<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>stale-issue</h1></td>
  </tr>
</table>

Reusable workflow that flags and closes stale issues. Wraps the [`stale`](../src/config/stale/README.md) composite with PR scanning disabled, so the run only touches issues.

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `days_before_stale` | Days of issue inactivity before applying the stale label | No | `60` |
| `days_before_close` | Days after an issue is marked stale before it is closed | No | `14` |
| `exempt_labels` | Comma-separated labels exempting an issue from the stale scan | No | `no-stale,security,pinned` |
| `operations_per_run` | Maximum API operations per run | No | `60` |
| `dry_run` | Preview changes without applying them | No | `false` |

## Usage

### Testing (against `@develop`)

```yaml
jobs:
  stale-issue:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/stale-issue.yml@develop
    with:
      dry_run: true
    secrets: inherit
```

### Production (pinned)

```yaml
jobs:
  stale-issue:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/stale-issue.yml@vX.Y.Z
    secrets: inherit
```

## Permissions required

```yaml
permissions:
  issues: write
```
