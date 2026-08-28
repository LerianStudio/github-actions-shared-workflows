<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>js-alpha-preview</h1></td>
  </tr>
</table>

Builds a disposable preview image from a product branch, so the work on that branch can be run somewhere before it is integrated anywhere.

**Nothing about this is a release.** No git tag, no GitHub release, no version bump, no GitOps update, no environment. The image is named after the product and the commit it was built from, and it is expected to be pruned once it ages out.

## What it produces

For a push to `develop-midaz` at commit `abc1234`:

```
ghcr.io/lerianstudio/alpha/product-console:midaz-alpha.202608272215.abc1234
docker.io/lerianstudio/product-console-alpha:midaz-alpha.202608272215.abc1234
```

The tag format `<product>-alpha.<utc>.<sha>` mirrors the Helm alpha convention and carries the `-alpha` substring that [`ghcr-alpha-cleanup`](ghcr-alpha-cleanup.md) looks for by default.

### Why the two names differ

Docker Hub has no nested namespaces: a repository is `org/name` and nothing deeper. `alpha/product-console` is a valid GHCR package and an invalid Docker Hub repository, so the marker moves from the namespace into the repository name there.

That difference has a consequence worth knowing: the retention tooling is GHCR-only. **Previews pushed to Docker Hub are not pruned automatically** — only the GHCR copy expires. Set `enable_dockerhub: false` if that matters more than reach.

## Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `runner_type` | string | `blacksmith-4vcpu-ubuntu-2404` | GitHub runner type |
| `branch_pattern` | string | `develop-*` | Glob matching the product branches that get a preview |
| `excluded_products` | string | `''` | Comma-separated products that must not get a preview |
| `image_name` | string | `''` | GHCR package. Must stay under `alpha/`. Empty → `alpha/<repo>` |
| `dockerhub_image_name` | string | `''` | Docker Hub repository, flat name. Empty → `<repo>-alpha` |
| `dockerhub_org` | string | `lerianstudio` | Docker Hub organization |
| `enable_dockerhub` | boolean | `true` | Also publish to Docker Hub |
| `dockerfile_name` | string | `Dockerfile` | Dockerfile name |
| `build_context` | string | `.` | Docker build context |
| `build_secrets` | string | `''` | Extra build secrets; npmrc is always included |
| `dry_run` | boolean | `false` | Build without pushing |

## Outputs

| Output | Description |
|--------|-------------|
| `published` | `'true'` when a preview was published for this ref |
| `reference` | Full GHCR reference of the preview, empty when none was published |

## Secrets

| Secret | Description |
|--------|-------------|
| `DOCKER_USERNAME` | Docker Hub username. Required when `enable_dockerhub` is true |
| `DOCKERHUB_IMAGE_PUSH_TOKEN` | Docker Hub push token. Required when `enable_dockerhub` is true |

GHCR authenticates with the automatic `GITHUB_TOKEN`.

## Usage

```yaml
name: Alpha Preview

on:
  push:
    branches:
      - 'develop-*'

jobs:
  preview:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/js-alpha-preview.yml@v1
    with:
      excluded_products: core
    secrets: inherit
```

A ref that does not match `branch_pattern` resolves to no product and the job does nothing, so the workflow is safe to point at a broader trigger than the product branches themselves.

## Required permissions

```yaml
permissions:
  contents: read
  packages: write
```
