# Build Workflow

Reusable workflow for building and pushing Docker images to container registries. Supports monorepo architectures with automatic change detection and multi-platform builds.

## Features

- **Monorepo support**: Automatic detection of changed components via filter_paths
- **Multi-registry**: Push to DockerHub and/or GitHub Container Registry (GHCR)
- **Smart platform builds**: Beta/RC tags build amd64 only, release tags build amd64+arm64
- **Semantic versioning**: Automatic tag extraction and Docker metadata
- **GitOps integration**: Upload artifacts for downstream gitops-update workflow
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

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `runner_type` | string | `firmino-lxc-runners` | GitHub runner type |
| `filter_paths` | string | `''` | Newline-separated list of path prefixes. If empty, builds from root (single-app mode) |
| `path_level` | string | `2` | Directory depth for app name extraction |
| `enable_dockerhub` | boolean | `true` | Enable pushing to DockerHub |
| `enable_ghcr` | boolean | `false` | Enable pushing to GitHub Container Registry |
| `dockerhub_org` | string | `lerianstudio` | DockerHub organization name |
| `ghcr_org` | string | `''` | GHCR organization (defaults to repository owner) |
| `dockerfile_name` | string | `Dockerfile` | Name of the Dockerfile |
| `app_name_prefix` | string | `''` | Prefix for app names in monorepo |
| `build_context` | string | `.` | Docker build context |
| `enable_gitops_artifacts` | boolean | `false` | Upload artifacts for gitops-update workflow |

## Secrets

Uses `secrets: inherit` pattern. Required secrets:

| Secret | Description | Required When |
|--------|-------------|---------------|
| `DOCKER_USERNAME` | DockerHub username | `enable_dockerhub: true` |
| `DOCKER_PASSWORD` | DockerHub password/token | `enable_dockerhub: true` |
| `MANAGE_TOKEN` | GitHub token for GHCR | `enable_ghcr: true` |
| `SLACK_WEBHOOK_URL` | Slack webhook for notifications | Optional |

## Platform Build Strategy

The workflow automatically selects platforms based on the tag type:

| Tag Type | Example | Platforms | Rationale |
|----------|---------|-----------|-----------|
| Beta | `v1.0.0-beta.1` | `linux/amd64` | Faster CI for development |
| RC | `v1.0.0-rc.1` | `linux/amd64` | Faster CI for staging |
| Release | `v1.0.0` | `linux/amd64,linux/arm64` | Full multi-arch support |

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
- Builds and pushes Docker images
- Creates GitOps artifacts if enabled

### notify
- Sends Slack notification on completion

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

**Solution**: ARM64 builds only run on release tags. Beta/RC tags build amd64 only for faster CI.

## Related Workflows

- [GitOps Update](gitops-update-workflow.md) - Update deployments after build
- [Release](release-workflow.md) - Create releases that trigger builds
- [Slack Notify](slack-notify-workflow.md) - Notification system

---

**Last Updated:** 2025-12-09
**Version:** 1.0.0
