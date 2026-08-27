<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>ghcr-alpha-cleanup</h1></td>
  </tr>
</table>

Prunes disposable alpha artifacts from a **single** GHCR package. Alphas are ephemeral by design — a preview image or chart built from a product branch — so they are deleted once they age past the TTL, or on demand when the branch that produced them has been integrated.

Deletion is irreversible, so the workflow validates its own scope before it runs and refuses anything that could reach beyond the alpha versions of the package it was pointed at.

## Why this exists alongside `helm-alpha-cleanup`

[`helm-alpha-cleanup.yml`](helm-alpha-cleanup.md) targets `alpha/*` by default, which spans **every** alpha package in the organization. That was harmless while charts were the only alpha artifact. Once a repository also publishes alpha *images* under the same `alpha/` prefix, a glob run from one repository reaches the other's artifacts.

This workflow is the artifact-agnostic version with that gap closed: the package must be named exactly, so a run is always confined to one package owned by one repository.

## Scope validation

The run fails before touching GHCR unless all of the following hold:

| Rule | Rejected example | Why |
|---|---|---|
| `image_names` is non-empty | `''` | An empty target is a configuration error, not "everything" |
| Every entry is `alpha/`-scoped | `product-console` | Release packages must be unreachable |
| No entry contains a glob (`*`, `?`, `[`) | `alpha/*` | A glob spans other repositories' alpha packages |
| `image_tags` is non-empty | `''` | Would select every version in the package |
| `image_tags` contains `alpha` | `*`, `v1.12.0` | Only alpha versions may be deleted |

The `alpha/` prefix check also runs inside the [`ghcr-alpha-cleanup`](../src/config/ghcr-alpha-cleanup/README.md) composite; the rules above are the outer layer and cover the two cases the prefix alone allows.

## Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `account` | string | `lerianstudio` | GitHub org/user that owns the package |
| `image_names` | string | — (**required**) | Exact package name(s), space-separated. Must be `alpha/`-scoped, no globs |
| `image_tags` | string | `*-alpha*` | Tag globs to target within those packages. Must contain `alpha` |
| `cut_off` | string | `3d` | Delete versions older than this. Use `1s` to purge on demand |
| `keep_n_most_recent` | number | `5` | Minimum recent versions kept. Counted **per package**, not per product |
| `dry_run` | boolean | `true` | Preview deletions without applying them |

`dry_run` defaults to `true` because this workflow deletes. Callers opt into real deletion explicitly.

## Secrets

| Secret | Description |
|--------|-------------|
| `GHCR_CLEANUP_PAT` | PAT with `delete:packages`. Required — `GITHUB_TOKEN` cannot delete organization-level packages, and App tokens are not guaranteed to either |

## Usage

### Scheduled TTL plus a manual entrypoint

```yaml
name: Alpha Cleanup

on:
  schedule:
    - cron: "0 4 * * *"
  workflow_dispatch:
    inputs:
      product:
        description: Which product's alphas to prune
        type: choice
        options: [all, midaz, tracer]
        default: all
      dry_run:
        description: Preview without deleting
        type: boolean
        default: true

jobs:
  cleanup:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/ghcr-alpha-cleanup.yml@v1
    with:
      image_names: alpha/product-console
      image_tags: >-
        ${{ (github.event_name == 'schedule' || inputs.product == 'all')
            && '*-alpha*' || format('{0}-alpha.*', inputs.product) }}
      dry_run: ${{ github.event_name == 'schedule' && false || inputs.dry_run }}
    secrets:
      GHCR_CLEANUP_PAT: ${{ secrets.GHCR_CLEANUP_PAT }}
```

### On-demand purge after a product branch is integrated

Once a product branch is merged, its previews are dead weight. `cut_off: 1s` with `keep_n_most_recent: 0` removes them immediately instead of waiting for the TTL.

```yaml
jobs:
  purge:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/ghcr-alpha-cleanup.yml@v1
    with:
      image_names: alpha/product-console
      image_tags: 'midaz-alpha.*'
      cut_off: '1s'
      keep_n_most_recent: 0
      dry_run: false
    secrets:
      GHCR_CLEANUP_PAT: ${{ secrets.GHCR_CLEANUP_PAT }}
```

## Naming constraint on products sharing a package

When several products publish into one package, their tags are told apart by prefix. A purge for `midaz` selects `midaz-alpha.*`, which does **not** match `midaz-v2-alpha....` — the character after `midaz` is `-v2`, not `-alpha`.

That is correct for distinct products, but it means a product whose name is a prefix of another is **not** covered by the other's purge. Both are still collected by the scheduled TTL. Prefer product names that are not prefixes of one another.

## Known gap: untagged versions

The underlying composite runs with `tag-selection: tagged`, so only tagged versions are considered. Buildx also produces untagged manifests (attestation and provenance), which are never collected and accumulate indefinitely. This is negligible for charts and material for images. Tracked as a follow-up.

## Required permissions

```yaml
permissions:
  contents: read
  packages: write
```
