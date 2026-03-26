<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>backmerge-pr</h1></td>
  </tr>
</table>

Creates a PR to backmerge a source branch into a target branch when a direct push fails. Checks for existing open PRs to avoid duplicates.

Typically used as a fallback in the release workflow when the `@saithodev/semantic-release-backmerge` plugin fails to push directly (non-fast-forward).

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `github-token` | GitHub token with pull-requests write permission | Yes | |
| `source-branch` | Source branch to merge from (e.g., main) | Yes | |
| `target-branch` | Target branch to merge into | No | `develop` |
| `version` | Release version for the PR title | Yes | |

## Outputs

| Output | Description |
|--------|-------------|
| `pr-url` | URL of the created or existing PR |
| `pr-number` | Number of the created or existing PR |

## Usage as composite step

```yaml
- name: Create backmerge PR
  uses: LerianStudio/github-actions-shared-workflows/src/config/backmerge-pr@v1.x.x
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    source-branch: main
    target-branch: develop
    version: ${{ steps.semantic.outputs.new_release_version }}
```

## Usage in release workflow (fallback pattern)

```yaml
- name: Semantic Release
  uses: cycjimmy/semantic-release-action@v6
  id: semantic
  continue-on-error: true
  ...

- name: Backmerge PR fallback
  if: steps.semantic.outcome == 'failure' && steps.semantic.outputs.new_release_published == 'true'
  uses: LerianStudio/github-actions-shared-workflows/src/config/backmerge-pr@v1.x.x
  with:
    github-token: ${{ steps.app-token.outputs.token }}
    source-branch: ${{ github.ref_name }}
    version: ${{ steps.semantic.outputs.new_release_version }}
```

## Required permissions

```yaml
permissions:
  contents: read
  pull-requests: write
```
