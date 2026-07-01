<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>ghcr-alpha-cleanup</h1></td>
  </tr>
</table>

Composite action that enforces the TTL of alpha Helm chart packages on GHCR: it deletes package versions matching the alpha namespace and tag globs that are older than a cut-off. Wraps [snok/container-retention-policy](https://github.com/snok/container-retention-policy).

Three filters combine (AND) so nothing outside scope is ever removed:

- `image-names: alpha/*` — only the alpha namespace; **real releases are a different package name and are invisible to this action**.
- `image-tags: *-alpha*` — only alpha tags.
- `cut-off: 3d` — only versions older than the cut-off (fresh alphas are kept).

Plus `keep-n-most-recent` as a floor so it never wipes a package entirely, and `dry-run` (default `true`) to preview.

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `account` | Org/user that owns the packages | No | `lerianstudio` |
| `token` | Token with `delete:packages` (org-level needs a PAT) | Yes | — |
| `image-names` | Package name globs (space-separated) | No | `alpha/*` |
| `image-tags` | Tag globs to target | No | `*-alpha*` |
| `cut-off` | Delete versions older than this | No | `3d` |
| `keep-n-most-recent` | Minimum recent versions to keep per package | No | `5` |
| `dry-run` | Preview deletions without applying | No | `true` |

## Usage

### As a composite action

```yaml
jobs:
  cleanup:
    runs-on: ubuntu-latest
    steps:
      - uses: LerianStudio/github-actions-shared-workflows/src/config/ghcr-alpha-cleanup@v1
        with:
          token: ${{ secrets.GHCR_CLEANUP_PAT }}
          dry-run: "true"
```

### As a reusable workflow (recommended)

```yaml
jobs:
  cleanup:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/helm-alpha-cleanup.yml@v1
    with:
      dry_run: false
    secrets:
      GHCR_CLEANUP_PAT: ${{ secrets.GHCR_CLEANUP_PAT }}
```

## Permissions / token

`GITHUB_TOKEN` cannot delete org-level packages — provide a **PAT with `delete:packages`** (and `read:packages`) via `token`.
