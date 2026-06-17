<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>go-release</h1></td>
  </tr>
</table>

Umbrella reusable workflow for Go **service** repositories (deployable apps that ship as container images). A caller references this single workflow and it drives the full release pipeline, branching on the pushed ref:

- **Branch push** → change gate (`src/config/non-doc-changes`) → semantic release (`release.yml`). Documentation-only pushes skip the release.
- **Tag push** → container build & push (`build.yml`) → GitOps update (`gitops-update.yml`), gated on the build actually producing images.

> **Note** — As of v1.x this workflow hosts the service release pipeline (semantic-release + Docker build + GitOps). The previous GoReleaser-based binary release pipeline remains available in the Git history of this file.

## Inputs

| Input | Description | Type | Default |
|-------|-------------|------|---------|
| `runner_type` | GitHub runner type | string | `blacksmith-4vcpu-ubuntu-2404` |
| `dry_run` | Reserved (downstream workflows have no dry-run mode yet) | boolean | `false` |
| `ignore_globs` | Space-separated globs treated as docs/meta for the branch-push gate | string | `*.md docs/* .github/* LICENSE* .gitignore` |
| `semantic_version` | semantic-release version | string | `23.0.8` |
| `enable_changelog` | Generate CHANGELOG.md via GPT after a successful release | boolean | `false` |
| `enable_major_tag` | Force-update the floating major tag (e.g. `v1`) | boolean | `false` |
| `stable_releases_only` | Only generate changelogs for stable releases | boolean | `true` |
| `enable_dockerhub` | Push image to DockerHub | boolean | `true` |
| `enable_ghcr` | Push image to GitHub Container Registry (requires `MANAGE_TOKEN`) | boolean | `true` |
| `enable_gitops_artifacts` | Upload GitOps artifacts for the downstream update | boolean | `false` |
| `app_name` | Override app/image name (single-app mode) | string | `''` (repo name) |
| `docker_build_args` | Newline-separated Docker build args | string | `''` |
| `enable_cosign_sign` | Sign images with cosign keyless (OIDC) | boolean | `true` |
| `enable_gitops_update` | Run the gitops-update job on tag push | boolean | `true` |
| `gitops_repository` | GitOps repository to update (org/repo) | string | `LerianStudio/midaz-firmino-gitops` |
| `gitops_artifact_pattern` | Pattern to download GitOps artifacts | string | `''` |
| `gitops_yaml_key_mappings` | JSON mapping of artifact names to YAML keys | string | `''` |
| `shared_paths` | Path patterns that trigger a release/build for all components | string | `''` |
| `filter_paths` | Path prefixes to filter (empty = single-app repo) | string | `''` |

## Secrets

| Secret | Description | Required |
|--------|-------------|----------|
| `MANAGE_TOKEN` | Token for release commits, tags and private module access | No |
| `SLACK_WEBHOOK_URL` | Slack webhook for pipeline notifications | No |
| `HELM_REPO_TOKEN` | Token for dispatching Helm chart updates (when enabled in build) | No |

## Usage

```yaml
name: Release Pipeline
on:
  push:
    branches: [main, release-candidate, develop]
    tags: ['**']

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: false

permissions:
  id-token: write
  contents: write
  issues: write
  pull-requests: write
  packages: write

jobs:
  pipeline:
    # Testing: @develop or @feat/<branch> · Production: pinned @vX.Y.Z
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-release.yml@v1
    with:
      enable_changelog: ${{ github.ref == 'refs/heads/main' }}
      enable_ghcr: true
      enable_gitops_artifacts: true
      gitops_artifact_pattern: "gitops-tags-my-service"
      gitops_yaml_key_mappings: '{"my-service.tag": ".api.image.tag"}'
      shared_paths: |
        go.mod
        go.sum
        internal/
        pkg/
        migrations/
        Dockerfile
        Makefile
    secrets: inherit
```

## Permissions

The single caller job must grant the union of what the internal jobs need: `id-token: write`, `contents: write`, `packages: write`, `pull-requests: write`, `issues: write`.

## Related

- [release](./release-workflow.md) — semantic-release pipeline this umbrella calls
- [build](./build-workflow.md) — container build & push this umbrella calls
- [gitops-update](./gitops-update-workflow.md) — GitOps update this umbrella calls
- [go-pr-validation](./go-pr-validation.md) — the matching PR validation umbrella
