<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>branch-cleanup</h1></td>
  </tr>
</table>

Composite action that deletes stale branches (no commits for N days, no open PRs) and removes branches after PR merges. Protected branches and branches with GitHub protection rules are never deleted.

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `github-token` | GitHub token with `contents:write` and `pull-requests:read` | Yes | — |
| `stale-days` | Days without commits before a branch is stale | No | `30` |
| `dry-run` | Preview deletions without applying them | No | `false` |
| `protected-branches` | Comma-separated branch patterns to never delete | No | `main,master,develop,release/*,hotfix/*` |
| `merged-branch` | Branch to delete (enables merged-branch mode) | No | `""` |

## Usage

### As a composite action (stale scan)

```yaml
# Use @develop or your feature branch to test before releasing
jobs:
  cleanup:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: read
    steps:
      - uses: actions/checkout@v4
      - uses: LerianStudio/github-actions-shared-workflows/src/config/branch-cleanup@develop
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          stale-days: "30"
          dry-run: "true"
```

### As a composite action (merged branch)

```yaml
jobs:
  cleanup:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: LerianStudio/github-actions-shared-workflows/src/config/branch-cleanup@v1.0.0
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          merged-branch: ${{ github.head_ref }}
```

### As a reusable workflow (recommended)

```yaml
jobs:
  cleanup:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/branch-cleanup.yml@v1.0.0
    with:
      stale_days: 30
      dry_run: true
    secrets: inherit
```

## Permissions required

```yaml
permissions:
  contents: write
  pull-requests: read
```
