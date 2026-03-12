<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>labels-sync</h1></td>
  </tr>
</table>

Composite action that syncs GitHub labels from a YAML definition file to a repository. Wraps [crazy-max/ghaction-github-labeler](https://github.com/crazy-max/ghaction-github-labeler).

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `github-token` | GitHub token with `issues:write` permission | Yes | — |
| `config` | Path to the labels YAML definition file | No | `.github/labels.yml` |
| `dry-run` | Preview changes without applying them | No | `false` |
| `skip-delete` | Skip deletion of labels absent from the config | No | `false` |

## Labels file format

Create a `.github/labels.yml` in the target repository:

```yaml
- name: bug
  color: "d73a4a"
  description: Something is not working as expected

- name: enhancement
  color: "a2eeef"
  description: New feature or improvement request

- name: documentation
  color: "0e8a16"
  description: Improvements or additions to documentation
```

## Usage

### As a composite action (inline step)

```yaml
jobs:
  sync:
    runs-on: ubuntu-latest
    permissions:
      issues: write
      contents: read
    steps:
      - uses: LerianStudio/github-actions-shared-workflows/src/config/labels-sync@v1.0.0
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

### As a reusable workflow (recommended)

```yaml
jobs:
  sync:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/labels-sync.yml@v1.0.0
    with:
      dry_run: false
    secrets: inherit
```

### Dry run (preview only)

```yaml
# Use @develop or your feature branch to test before releasing
- uses: LerianStudio/github-actions-shared-workflows/src/config/labels-sync@develop
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    dry-run: "true"
```

### Sync without deleting unlisted labels

```yaml
- uses: LerianStudio/github-actions-shared-workflows/src/config/labels-sync@v1.0.0
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    skip-delete: "true"
```

## Permissions required

```yaml
permissions:
  issues: write
  contents: read
```

## When to run

The recommended trigger pattern is to run automatically on changes to the labels file, with a manual fallback for the initial setup:

```yaml
on:
  push:
    branches:
      - main
    paths:
      - ".github/labels.yml"
  workflow_dispatch:
    inputs:
      dry_run:
        type: boolean
        default: false
```
