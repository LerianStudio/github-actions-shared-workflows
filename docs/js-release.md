<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>js-release</h1></td>
  </tr>
</table>

Umbrella reusable workflow for JavaScript/TypeScript **service** repositories (deployable apps that ship as container images). A caller references this single workflow and it drives the full release pipeline, branching on the pushed ref:

- **Branch push** → change gate (`src/config/non-doc-changes`) → semantic release (`release.yml`). Documentation-only pushes skip the release.
- **Tag push** → container build & push (`typescript-build.yml`) → GitOps update (`gitops-update.yml`), gated on the build actually producing images.

Mirrors the [`go-release`](./go-release-workflow.md) umbrella for Go services — providing the same single-caller DX for Next.js frontends, NestJS backends, and any JS/TS service that ships a Docker image.

### Repository layouts

`filter_paths` drives both the release matrix and the build matrix:

- **Single app** — `filter_paths` empty: one semantic-release tag, one image.
- **Per-component monorepo** — `filter_paths` set: each changed component gets its own release tag and its own image.

### npmrc auto-injection

`typescript-build.yml` always injects an npmrc for private `@lerianstudio` GitHub Packages dependencies — no extra configuration needed. Additional build secrets are additive via `build_secrets`.

## Inputs

| Input | Description | Type | Default |
|-------|-------------|------|---------|
| `runner_type` | GitHub runner type | string | `blacksmith-4vcpu-ubuntu-2404` |
| `dry_run` | Run semantic-release and build in dry-run mode (no tags/releases/images created) | boolean | `false` |
| `ignore_globs` | Space-separated globs treated as docs/meta for the branch-push gate | string | `*.md docs/* .github/* LICENSE* .gitignore` |
| `semantic_version` | semantic-release version | string | `23.0.8` |
| `filter_paths` | Path prefixes to filter (empty = single-app repo) | string | `''` |
| `shared_paths` | Path patterns that trigger a release/build for all components | string | `''` |
| `path_level` | Directory depth level to extract app name | string | `2` |
| `enable_dockerhub` | Push image to DockerHub | boolean | `false` |
| `enable_ghcr` | Push image to GitHub Container Registry | boolean | `true` |
| `enable_gitops_artifacts` | Upload GitOps artifacts for the downstream update | boolean | `false` |
| `app_name_prefix` | Prefix for app names in monorepo (e.g. `lerian-map` -> `lerian-map-agent`) | string | `''` |
| `app_name_overrides` | Explicit `path:name` app name mappings | string | `''` |
| `dockerfile_name` | Name of the Dockerfile | string | `Dockerfile` |
| `build_context` | Docker build context | string | `.` |
| `build_secrets` | Additional build secrets (one per line); npmrc is always injected | string | `''` |
| `enable_cosign_sign` | Sign images with cosign keyless (OIDC) | boolean | `true` |
| `dockerhub_org` | DockerHub organization name | string | `lerianstudio` |
| `force_full_matrix` | Build all `filter_paths` components on every tag regardless of what changed (use for tightly-coupled components that must always share the same image tag) | boolean | `false` |
| `enable_gitops_update` | Run the gitops-update job on tag push | boolean | `true` |
| `gitops_repository` | GitOps repository to update (org/repo). Empty → `GITOPS_REPOSITORY` org-level variable | string | `''` |
| `update_sandbox` | Include sandbox environment on production tags | boolean | `false` |
| `gitops_artifact_pattern` | Pattern to download GitOps artifacts. Empty → `gitops-tags-<repo-name>*` | string | `''` |
| `gitops_yaml_key_mappings` | JSON mapping of artifact names to YAML keys | string | `''` |
| `deployment_matrix_ref` | Git ref of shared-workflows to read the deployment matrix from | string | `main` |
| `enable_argocd_sync` | Trigger ArgoCD sync after updating the GitOps repo | boolean | `true` |
| `commit_message_prefix` | Prefix for the GitOps commit message. Empty → `app_name_prefix`, then repo name | string | `''` |
| `use_dynamic_mapping` | Use dynamic artifact-to-YAML key mapping | boolean | `false` |
| `configmap_updates` | JSON mapping of artifact names to configmap keys (helmfile only) | string | `''` |
| `enable_docker_login` | Log in to DockerHub in the gitops-update job | boolean | `false` |

## Secrets

| Secret | Description | Required |
|--------|-------------|----------|
| `MANAGE_TOKEN` | Token for release commits, tags and private module access | No |
| `SLACK_WEBHOOK_URL` | Slack webhook for pipeline notifications | No |

All other secrets required by the underlying primitives (GitHub App tokens, GPG key, DockerHub credentials, etc.) are forwarded automatically via `secrets: inherit`.

## Usage

### Single-app repository

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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/js-release.yml@v1
    with:
      enable_ghcr: true
      enable_gitops_artifacts: true
      gitops_repository: "LerianStudio/midaz-firmino-gitops"
      gitops_yaml_key_mappings: '{"lerian-map.tag": ".lerian-map.image.tag"}'
    secrets: inherit
```

### Monorepo with tightly-coupled components

Use `force_full_matrix: true` when components must always be released together with the same image tag:

```yaml
jobs:
  pipeline:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/js-release.yml@v1
    with:
      enable_ghcr: true
      enable_gitops_artifacts: true
      app_name_prefix: "plugin-access-manager"
      filter_paths: |
        components/auth
        components/identity
      force_full_matrix: true
      gitops_repository: "LerianStudio/midaz-firmino-gitops"
      gitops_yaml_key_mappings: '{"plugin-access-manager-auth.tag": ".auth.image.tag", "plugin-access-manager-identity.tag": ".identity.image.tag"}'
    secrets: inherit
```

### Replacing two caller files with one

Before — two workflow files in the caller repo:

```yaml
# release.yml
jobs:
  release:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/typescript-release.yml@v1
    secrets: inherit

# build.yml
jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/typescript-build.yml@v1
    with:
      enable_ghcr: true
      enable_gitops_artifacts: true
    secrets: inherit

  gitops:
    needs: build
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@v1
    with:
      gitops_repository: "LerianStudio/midaz-firmino-gitops"
      yaml_key_mappings: '{"my-app.tag": ".api.image.tag"}'
    secrets: inherit
```

After — one workflow file:

```yaml
# release.yml
jobs:
  pipeline:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/js-release.yml@v1
    with:
      enable_ghcr: true
      enable_gitops_artifacts: true
      gitops_repository: "LerianStudio/midaz-firmino-gitops"
      gitops_yaml_key_mappings: '{"my-app.tag": ".api.image.tag"}'
    secrets: inherit
```

## Permissions

The single caller job must grant the union of what the internal jobs need:

```yaml
permissions:
  id-token: write
  contents: write
  issues: write
  pull-requests: write
  packages: write
```

## Related

- [release](./release.md) — semantic-release pipeline this umbrella calls on branch push
- [typescript-build](./typescript-build.md) — container build & push this umbrella calls
- [gitops-update](./gitops-update-workflow.md) — GitOps update this umbrella calls
- [go-release](./go-release-workflow.md) — the equivalent umbrella for Go service repositories
