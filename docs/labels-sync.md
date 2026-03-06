<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>labels-sync</h1></td>
  </tr>
</table>

Reusable workflow that syncs GitHub labels from a YAML definition file to a repository. Uses the [`src/config/labels-sync`](../src/config/labels-sync/README.md) composite action internally.

## What it does

Reads a `.github/labels.yml` file and applies its label definitions to the target repository — creating missing labels, updating colors and descriptions, and optionally deleting labels that are no longer in the file.

## Inputs

| Input | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `config` | `string` | No | `.github/labels.yml` | Path to the labels YAML definition file |
| `dry_run` | `boolean` | No | `false` | Preview changes without applying them |
| `skip_delete` | `boolean` | No | `false` | Skip deletion of labels absent from the config |

## Secrets

| Secret | Required | Description |
|---|---|---|
| `GITHUB_TOKEN` | No | Defaults to the automatic token; needs `issues:write` |

## Labels file format

Create a `.github/labels.yml` in the caller repository:

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

### Sync on labels file change

```yaml
# .github/workflows/labels-sync.yml
name: Sync Labels

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

jobs:
  sync:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/labels-sync.yml@v1.0.0
    with:
      dry_run: ${{ inputs.dry_run || false }}
    secrets: inherit
```

### Dry run (preview only)

```yaml
# Use @develop or your feature branch to validate before releasing
jobs:
  preview:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/labels-sync.yml@develop
    with:
      dry_run: true
    secrets: inherit
```

### Sync without deleting unlisted labels

```yaml
jobs:
  sync:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/labels-sync.yml@v1.0.0
    with:
      skip_delete: true
    secrets: inherit
```

### Custom labels file path

```yaml
jobs:
  sync:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/labels-sync.yml@v1.0.0
    with:
      config: ".github/custom-labels.yml"
    secrets: inherit
```

## Permissions

```yaml
permissions:
  issues: write
  contents: read
```

## Self-use in this repository

This repo uses `self-labels-sync.yml` as a thin entrypoint that calls this workflow via local path. Reusable workflows must not have autonomous push triggers — those belong in a dedicated `self-` file.
