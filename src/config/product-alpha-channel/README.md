<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>product-alpha-channel</h1></td>
  </tr>
</table>

Resolves the `semantic-release` branches config and tag format for a per-product alpha line, deriving the product name from the branch being released. A repo where each product owns a `develop-<product>` branch can then publish isolated alpha tags — `develop-midaz` produces `midaz-v1.0.0-alpha.1`, `develop-tracer` produces `tracer-v1.0.0-alpha.1` — while the unified `develop`, `release-candidate` and `main` lines keep using the caller's own `.releaserc`.

The action only computes values; it never writes a config file or creates a tag. `release.yml` feeds the outputs to the `branches` and `tag_format` inputs of `cycjimmy/semantic-release-action`, which override the caller's `.releaserc` for that run. Both outputs are empty when the branch does not match, and the action drops empty inputs, so non-product branches are untouched.

## Why this shape

`semantic-release` has no per-branch `tagFormat`: the option is global to a run. Overriding `branches` and `tagFormat` per run is the only way to give each product its own tag line without maintaining one config file per product in every consuming repo.

The generated `branches` list always includes `anchor-branch`. `semantic-release` validates that at least one release (non-prerelease) branch is configured — see `release.branchesValidator` in `lib/definitions/branches.js` — and aborts with `ERELEASEBRANCHES` on a list containing only prerelease entries.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `ref-name` | Branch name being released (e.g. `github.ref_name`) | Yes | |
| `branch-pattern` | Glob matching product branches. The text replacing `*` becomes the product name. | No | `develop-*` |
| `anchor-branch` | Release branch included in the generated config, required for the config to validate | No | `main` |
| `prerelease-id` | `semantic-release` prerelease identifier for the product line | No | `alpha` |
| `tag-format-template` | Tag format for the product line. `{product}` is replaced by the resolved product name; `${version}` is left for `semantic-release` to expand. | No | `{product}-v${version}` |
| `excluded-products` | Comma-separated product names that must not get an alpha line, even when the branch matches the pattern | No | `''` |

## Outputs

| Output | Description |
|--------|-------------|
| `is-alpha` | `'true'` when `ref-name` matches `branch-pattern` and the product is not excluded |
| `product` | Product name extracted from the branch, empty when `is-alpha` is `'false'` |
| `branches` | JSON branches config to override `semantic-release` with, empty when `is-alpha` is `'false'` |
| `tag-format` | Tag format to override `semantic-release` with, empty when `is-alpha` is `'false'` |

For `develop-midaz` with the defaults:

```json
[{"name":"main"},{"name":"develop-midaz","prerelease":"alpha"}]
```

The action fails the run when `branch-pattern` has no `*`, when the extracted product name does not match `^[a-z0-9][a-z0-9-]*$`, or when `ref-name` equals `anchor-branch`.

## Version baseline

A product line starts from scratch: no tag matches `<product>-v*` on the first run, so `semantic-release` falls back to `FIRST_RELEASE` and publishes `<product>-v1.0.0-alpha.1`. The repo's existing `v*` tags are invisible to that calculation because they do not match the tag format. To start a product from another baseline, push an annotated tag in the product format (e.g. `midaz-v0.1.0`) before the first alpha run.

## Usage as composite step

```yaml
jobs:
  release:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - name: Resolve product alpha channel
        id: alpha
        uses: LerianStudio/github-actions-shared-workflows/src/config/product-alpha-channel@v1.x.x
        with:
          ref-name: ${{ github.ref_name }}
          branch-pattern: 'develop-*'
          anchor-branch: main
          excluded-products: core

      - name: Semantic Release
        uses: cycjimmy/semantic-release-action@<sha> # v6
        with:
          ci: false
          working_directory: ${{ matrix.app.working_dir }}
          branches: ${{ steps.alpha.outputs.branches }}
          tag_format: ${{ steps.alpha.outputs.tag-format }}
```

## Usage as reusable workflow

```yaml
name: Release

on:
  push:
    branches: [develop, develop-*, release-candidate, main]

jobs:
  release:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/js-release.yml@v1.x.x
    with:
      product_alpha_enabled: true
      product_alpha_branch_pattern: 'develop-*'
      product_alpha_excluded_products: 'core'
    secrets: inherit
```

The consuming repo must add the product branches to its `on.push.branches` — the alpha line is never reached otherwise.

## Required permissions

```yaml
permissions:
  contents: read
```
