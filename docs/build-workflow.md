# Build Workflow

Reusable workflow for building and pushing Docker images to container registries. Supports monorepo architectures with automatic change detection and multi-platform builds.

## Features

- **Monorepo support**: Automatic detection of changed components via filter_paths
- **Multi-registry**: Push to DockerHub and/or GitHub Container Registry (GHCR)
- **Smart platform builds**: Beta/RC tags build amd64 only, release tags build amd64+arm64 (overridable with `force_multiplatform`)
- **Semantic versioning**: Automatic tag extraction and Docker metadata
- **GitOps integration**: Upload artifacts for downstream gitops-update workflow
- **Docker build arguments**: Pass custom build args with `{APP_NAME}` placeholder for monorepo-aware Dockerfiles
- **Helm chart dispatch**: Automatic Helm repository updates on release
- **Slack notifications**: Automatic success/failure notifications

## Usage

### Single App Repository

```yaml
name: Build
on:
  push:
    tags:
      - '**'

jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/build.yml@main
    with:
      runner_type: "firmino-lxc-runners"
      enable_dockerhub: true
      enable_ghcr: true
      dockerhub_org: lerianstudio
    secrets: inherit
```

### Monorepo with Multiple Components

```yaml
name: Build
on:
  push:
    tags:
      - '**'

jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/build.yml@main
    with:
      runner_type: "firmino-lxc-runners"
      filter_paths: |-
        components/onboarding
        components/transaction
        components/console
      path_level: 2
      app_name_prefix: "midaz"
      enable_dockerhub: true
      enable_ghcr: true
      dockerhub_org: lerianstudio
      enable_gitops_artifacts: true
    secrets: inherit
```

### Monorepo with Shared Dockerfile (build_args)

When using a single Dockerfile at the repo root that relies on a build argument to select the site/app:

```yaml
name: Build
on:
  release:
    types: [published]

jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/build.yml@main
    with:
      filter_paths: |
        sites/
      path_level: '2'
      enable_dockerhub: true
      enable_gitops_artifacts: true
      build_context: '.'
      build_args: |
        SITE={APP_NAME}
    secrets: inherit
```

The `{APP_NAME}` placeholder is automatically replaced with the detected app name from the matrix (e.g., `sites/tracer` → `SITE=tracer`).

### With GitOps Update

```yaml
name: Build
on:
  push:
    tags:
      - '**'

jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/build.yml@main
    with:
      filter_paths: |-
        components/api
        components/worker
      path_level: 2
      app_name_prefix: "myapp"
      enable_gitops_artifacts: true
    secrets: inherit

  update_gitops:
    needs: [build]
    if: contains(github.ref, '-beta') || contains(github.ref, '-rc')
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@main
    with:
      gitops_repository: "MyOrg/gitops-repo"
      artifact_pattern: "gitops-tags-myapp-*"
    secrets: inherit
```

## Inputs

### Core

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `runner_type` | string | `blacksmith-4vcpu-ubuntu-2404` | GitHub runner type |
| `filter_paths` | string | `''` | Newline-separated list of path prefixes. If empty, builds from root (single-app mode) |
| `path_level` | string | `2` | Directory depth for app name extraction |
| `normalize_to_filter` | boolean | `true` | Normalize changed paths to their filter path. Recommended for monorepos to avoid duplicate builds |

### Registry

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `enable_dockerhub` | boolean | `true` | Enable pushing to DockerHub |
| `enable_ghcr` | boolean | `false` | Enable pushing to GitHub Container Registry |
| `dockerhub_org` | string | `lerianstudio` | DockerHub organization name |
| `ghcr_org` | string | `''` | GHCR organization (defaults to repository owner) |

### Docker Build

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `dockerfile_name` | string | `Dockerfile` | Name of the Dockerfile |
| `build_context` | string | `.` | Docker build context |
| `build_args` | string | `''` | Newline-separated Docker build arguments. Use `{APP_NAME}` as placeholder for the detected app name (e.g., `SITE={APP_NAME}`) |
| `force_multiplatform` | boolean | `false` | Force multi-platform build (amd64+arm64) even for beta/rc tags |

### App Naming

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `app_name_prefix` | string | `''` | Prefix for app names in monorepo (e.g., `midaz` results in `midaz-agent`) |
| `app_name_overrides` | string | `''` | Explicit app name mappings in `path:name` format. Overrides default extraction for matched paths |

### GitOps

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `enable_gitops_artifacts` | boolean | `false` | Upload artifacts for downstream gitops-update workflow |

### Helm Dispatch

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `enable_helm_dispatch` | boolean | `false` | Enable dispatching to Helm repository for chart updates |
| `helm_repository` | string | `LerianStudio/helm` | Helm repository to dispatch to (org/repo format) |
| `helm_chart` | string | `''` | Helm chart name to update |
| `helm_target_ref` | string | `main` | Target branch in Helm repository |
| `helm_components_base_path` | string | `components` | Base path for components in source repo |
| `helm_env_file` | string | `.env.example` | Env example file name relative to component path |
| `helm_detect_env_changes` | boolean | `true` | Whether to detect new environment variables for Helm |
| `helm_dispatch_on_rc` | boolean | `false` | Enable Helm dispatch for release-candidate (rc) tags |
| `helm_dispatch_on_beta` | boolean | `false` | Enable Helm dispatch for beta tags |
| `helm_values_key_mappings` | string | `''` | JSON mapping of component names to values.yaml keys |

## Secrets

Uses `secrets: inherit` pattern. Required secrets:

| Secret | Description | Required When |
|--------|-------------|---------------|
| `DOCKER_USERNAME` | DockerHub username | `enable_dockerhub: true` |
| `DOCKER_PASSWORD` | DockerHub password/token | `enable_dockerhub: true` |
| `MANAGE_TOKEN` | GitHub token for GHCR and build secrets | `enable_ghcr: true` or always (used as build secret) |
| `SLACK_WEBHOOK_URL` | Slack webhook for notifications | Optional |
| `HELM_REPO_TOKEN` | Token for Helm repository dispatch | `enable_helm_dispatch: true` |

## Platform Build Strategy

The workflow automatically selects platforms based on the tag type:

| Tag Type | Example | Platforms | Rationale |
|----------|---------|-----------|-----------|
| Beta | `v1.0.0-beta.1` | `linux/amd64` | Faster CI for development |
| RC | `v1.0.0-rc.1` | `linux/amd64` | Faster CI for staging |
| Release | `v1.0.0` | `linux/amd64,linux/arm64` | Full multi-arch support |

> Set `force_multiplatform: true` to override and build both platforms for beta/rc tags.

## Docker Image Tags

Generated tags based on semantic versioning:

| Tag Pattern | Example | When Applied |
|-------------|---------|--------------|
| `{{version}}` | `1.0.0-beta.1` | Always |
| `{{major}}.{{minor}}` | `1.0` | Always |
| `{{major}}` | `1` | Release tags only |

## Monorepo Change Detection

When `filter_paths` is provided, the workflow:

1. Detects which components have changes in the tagged commit
2. Builds only the changed components
3. Names images using the pattern: `{app_name_prefix}-{component_name}`

**Example:**

```yaml
filter_paths: |-
  components/api
  components/worker
app_name_prefix: "myapp"
```

Changed files in `components/api/` → Builds `myapp-api` image
Changed files in `components/worker/` → Builds `myapp-worker` image

## Docker Build Arguments

When `build_args` is provided, the workflow resolves `{APP_NAME}` placeholders before passing arguments to `docker build`. This is useful for monorepos with a shared Dockerfile that selects sub-projects via `ARG`.

**Example Dockerfile:**

```dockerfile
ARG SITE
WORKDIR /app
COPY sites/${SITE} sites/${SITE}
```

**Caller workflow:**

```yaml
build_args: |
  SITE={APP_NAME}
```

If the detected app is `tracer` (from `sites/tracer`), the build receives `--build-arg SITE=tracer`.

Multiple build args are supported (one per line):

```yaml
build_args: |
  SITE={APP_NAME}
  NODE_ENV=production
```

## GitOps Artifacts

When `enable_gitops_artifacts: true`:

1. Creates artifact files with version tags (without `v` prefix)
2. Uploads as GitHub Actions artifacts
3. Can be consumed by `gitops-update.yml` workflow

**Artifact pattern:** `gitops-tags-{app_name}`

## Slack Notifications

Automatically sends notifications on completion:

- ✅ **Success**: Green notification with workflow details
- ❌ **Failure**: Red notification with failed job names
- Skipped if `SLACK_WEBHOOK_URL` secret is not configured

## Workflow Jobs

### prepare
- Detects changed paths (monorepo) or sets single-app mode
- Determines build platforms based on tag type
- Outputs matrix for build job

### build
- Runs for each component in the matrix
- Resolves build arguments (replaces `{APP_NAME}` placeholders)
- Builds and pushes Docker images
- Creates GitOps artifacts if enabled

### notify
- Sends Slack notification on completion

### dispatch-helm
- Dispatches to Helm repository for chart updates (when `enable_helm_dispatch: true`)
- By default only runs on production releases; can be enabled for rc/beta via `helm_dispatch_on_rc` and `helm_dispatch_on_beta`

## Best Practices

1. **Use semantic versioning tags**: `v1.0.0`, `v1.0.0-beta.1`, `v1.0.0-rc.1`
2. **Enable both registries**: DockerHub for public access, GHCR for GitHub integration
3. **Use GitOps artifacts**: For automated deployment pipelines
4. **Configure Slack**: For build notifications to your team channel

## Troubleshooting

### No builds triggered

**Issue**: Workflow runs but no images are built

**Solution**: 
- For monorepo: Ensure changed files are within `filter_paths`
- Check tag format matches expected pattern

### GHCR authentication fails

**Issue**: Cannot push to GitHub Container Registry

**Solution**:
- Ensure `MANAGE_TOKEN` has `packages: write` permission
- Check repository visibility settings

### Slow multi-arch builds

**Issue**: ARM64 builds take too long

**Solution**: ARM64 builds only run on release tags. Beta/RC tags build amd64 only for faster CI. Use `force_multiplatform: true` to override this behavior.

### Docker build fails with missing ARG

**Issue**: Dockerfile uses `ARG` (e.g., `ARG SITE`) but the build fails because the argument is not passed.

**Solution**: Use the `build_args` input with the `{APP_NAME}` placeholder:
```yaml
build_args: |
  SITE={APP_NAME}
```

## Related Workflows

- [GitOps Update](gitops-update-workflow.md) - Update deployments after build
- [Release](release-workflow.md) - Create releases that trigger builds
- [Slack Notify](slack-notify-workflow.md) - Notification system

- [Helm Dispatch](dispatch-helm-workflow.md) - Automatic Helm chart updates

---

**Last Updated:** 2026-03-03
**Version:** 1.14.0
