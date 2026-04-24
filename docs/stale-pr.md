<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>stale-pr</h1></td>
  </tr>
</table>

Reusable workflow that flags and closes stale pull requests. Wraps the [`stale`](../src/config/stale/README.md) composite with issue scanning disabled, so the run only touches PRs.

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `days_before_stale` | Days of PR inactivity before applying the stale label | No | `30` |
| `days_before_close` | Days after a PR is marked stale before it is closed | No | `14` |
| `exempt_labels` | Comma-separated labels exempting a PR from the stale scan | No | `no-stale,security,work-in-progress` |
| `operations_per_run` | Maximum API operations per run | No | `60` |
| `dry_run` | Preview changes without applying them | No | `false` |

## Usage

### Testing (against `@develop`)

```yaml
jobs:
  stale-pr:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/stale-pr.yml@develop
    with:
      dry_run: true
    secrets: inherit
```

### Production (pinned)

```yaml
jobs:
  stale-pr:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/stale-pr.yml@vX.Y.Z
    secrets: inherit
```

## Permissions required

```yaml
permissions:
  pull-requests: write
```
