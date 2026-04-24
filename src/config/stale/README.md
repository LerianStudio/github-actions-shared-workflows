<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>stale</h1></td>
  </tr>
</table>

Composite action that flags and closes stale PRs and issues. Wraps [actions/stale](https://github.com/actions/stale) with Lerian defaults and a consistent `dry-run` switch (mapped to the action's `debug-only` flag).

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `github-token` | GitHub token with `pull-requests:write` and `issues:write` | Yes | — |
| `days-before-pr-stale` | Days of PR inactivity before applying the stale label | No | `30` |
| `days-before-pr-close` | Days after a PR is marked stale before it is closed | No | `14` |
| `days-before-issue-stale` | Days of issue inactivity before applying the stale label | No | `60` |
| `days-before-issue-close` | Days after an issue is marked stale before it is closed | No | `14` |
| `stale-pr-label` | Label applied to stale PRs | No | `stale` |
| `stale-issue-label` | Label applied to stale issues | No | `stale` |
| `exempt-pr-labels` | Comma-separated labels exempting a PR from stale scan | No | `no-stale,security,work-in-progress` |
| `exempt-issue-labels` | Comma-separated labels exempting an issue from stale scan | No | `no-stale,security,pinned` |
| `exempt-draft-pr` | Skip draft PRs during the stale scan | No | `true` |
| `operations-per-run` | Maximum API operations per run | No | `60` |
| `dry-run` | Preview changes without applying them (maps to `debug-only`) | No | `false` |

## Usage

### As a composite action

```yaml
jobs:
  stale:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
      issues: write
    steps:
      - uses: LerianStudio/github-actions-shared-workflows/src/config/stale@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          dry-run: "true"
```

### As a reusable workflow (recommended)

```yaml
jobs:
  stale:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/stale.yml@v1
    with:
      dry_run: false
    secrets: inherit
```

## Permissions required

```yaml
permissions:
  pull-requests: write
  issues: write
```
