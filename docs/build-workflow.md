# Build Workflow

Reusable workflow for building and pushing Docker images to container registries. Supports monorepo architectures with automatic change detection and multi-platform builds.

## Features

- **Monorepo support**: Automatic detection of changed components via filter_paths
- **Multi-registry**: Push to DockerHub and/or GitHub Container Registry (GHCR)
- **Smart platform builds**: Beta/RC tags build amd64 only (unless `force_multiplatform` is enabled), release tags build amd64+arm64
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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/build.yml@v1.0.0
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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/build.yml@v1.0.0
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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/build.yml@v1.0.0
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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@v1.0.0
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
| `enable_ghcr` | boolean | `true` | Enable pushing to GitHub Container Registry (requires `MANAGE_TOKEN`) |
| `dockerhub_org` | string | `lerianstudio` | DockerHub organization name |
| `ghcr_org` | string | `''` | GHCR organization (defaults to repository owner) |
| `on_existing_tag` | string | `fail` | Behaviour when the target tag already exists in an enabled registry (pre-flight check before build): `fail` (abort early), `skip` (skip build/push, still emit GitOps artifacts for an idempotent re-run), `warn` (warn and build anyway) |
| `dockerfile_name` | string | `Dockerfile` | Name of the Dockerfile |
| `app_name_prefix` | string | `''` | Prefix for app names in monorepo |
| `build_context` | string | `.` | Docker build context |
| `enable_gitops_artifacts` | boolean | `false` | Upload artifacts for gitops-update workflow |
| `force_multiplatform` | boolean | `false` | Force multi-platform build (amd64+arm64) even for beta/rc tags |
| `enable_cosign_sign` | boolean | `true` | Sign images with cosign keyless (OIDC) signing. Requires `id-token: write` in caller |
| `cosign_max_attempts` | string | `3` | Max cosign signing attempts per image. Increase to absorb transient OIDC/Fulcio rate limits |
| `cosign_initial_delay` | string | `5` | Initial delay (seconds) between cosign retries. Grows ×3 each failed attempt |
| `continue_gitops_on_signing_failure` | boolean | `false` | Allow GitOps artifact upload to continue when cosign signing fails after all retries. Image stays unsigned in registry; manual `cosign sign` required |

## Secrets

Uses `secrets: inherit` pattern. Required secrets:

| Secret | Description | Required When |
|--------|-------------|---------------|
| `DOCKER_USERNAME` | DockerHub username | `enable_dockerhub: true` |
| `DOCKER_PASSWORD` | DockerHub password/token | `enable_dockerhub: true` |
| `MANAGE_TOKEN` | GitHub token for GHCR | `enable_ghcr: true` |
| `SLACK_WEBHOOK_URL` | Slack webhook for notifications | Optional |

## Tag Immutability and Re-runs

Before building, the workflow checks whether the target image tag already exists in each enabled registry (via `docker manifest inspect`, reusing the registry logins). This avoids a full rebuild that would only fail at push time on registries with tag immutability enabled. Behaviour is controlled by `on_existing_tag`:

- **`fail`** (default): abort early with a clear error instead of rebuilding then failing at push.
- **`skip`**: skip the build/push but still emit the GitOps tag artifacts (from the version), so a re-run remains idempotent for the downstream GitOps update.
- **`warn`**: emit a warning and build anyway (push may still fail on immutable registries).

A non-existent tag (or a check that errors out, e.g. transient registry issues) is treated as "not present" so the check never blocks a legitimate build.

## Platform Build Strategy

The workflow automatically selects platforms based on the tag type:

| Tag Type | `force_multiplatform` | Platforms | Rationale |
|----------|----------------------|-----------|-----------|
| Beta | `false` (default) | `linux/amd64` | Faster CI for development |
| Beta | `true` | `linux/amd64,linux/arm64` | Multi-arch needed in dev |
| RC | `false` (default) | `linux/amd64` | Faster CI for staging |
| RC | `true` | `linux/amd64,linux/arm64` | Multi-arch needed in staging |
| Release | N/A | `linux/amd64,linux/arm64` | Always full multi-arch support |

## Docker Image Tags

Generated tags based on semantic versioning:

| Tag Pattern | Example | When Applied |
|-------------|---------|--------------|
| `{{version}}` | `1.0.0-beta.1` | Always |
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

## Helm Dispatch

When `enable_helm_dispatch: true`, the workflow dispatches a chart update to the configured Helm repository (default: `LerianStudio/helm`) after a successful build.

### Default policy: production releases only

By default, Helm dispatch runs **only on production release tags** (non-`-rc`, non-`-beta`). This is enforced by:

- `helm_dispatch_on_rc` → `default: false`
- `helm_dispatch_on_beta` → `default: false`

This is intentional. RC and beta tags are pre-release artifacts — dispatching them to the Helm repo creates noisy PRs in `LerianStudio/helm` for charts that should not roll forward to staging or production.

### Opt-in for RC/beta dispatch (use sparingly)

Only enable `helm_dispatch_on_rc` or `helm_dispatch_on_beta` when there is a deliberate reason — for example, a chart that must be staged from RC builds in a specific environment. Document the reason in the caller workflow.

```yaml
# ✅ Correct — production-only dispatch (recommended)
jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/build.yml@v1.28.5
    with:
      enable_helm_dispatch: true
      helm_chart: my-chart
      # helm_dispatch_on_rc and helm_dispatch_on_beta default to false
    secrets: inherit
```

```yaml
# ⚠️ Opt-in — only when intentional, document why
jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/build.yml@v1.28.5
    with:
      enable_helm_dispatch: true
      helm_chart: my-chart
      helm_dispatch_on_rc: true   # staging environment promotes from RC tags
    secrets: inherit
```

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

## Image Signing (cosign)

Container images are signed by default using [Sigstore cosign](https://github.com/sigstore/cosign) with keyless (OIDC) signing. The GitHub Actions identity is used as proof of provenance — no private keys are needed.

### Caller permissions

Callers **must** grant `id-token: write` for signing to work:

```yaml
permissions:
  contents: read
  packages: write
  id-token: write   # required for cosign keyless signing
```

### Disabling signing

```yaml
jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/build.yml@v1.0.0
    with:
      enable_cosign_sign: false
    secrets: inherit
```

### Resilience: retries and GitOps continuation

Cosign signing depends on the Sigstore OIDC/Fulcio infrastructure, which can hit transient rate limits or 5xx responses. Two layers protect releases:

1. **Retry with exponential backoff** — controlled by `cosign_max_attempts` (default `3`) and `cosign_initial_delay` (default `5`s, grows ×3 between attempts). Increase both for releases that consistently brush against rate limits.

2. **Optional GitOps continuation** — when `continue_gitops_on_signing_failure: true`, signing failure does not block the GitOps artifact upload. The image is already pushed and immutable in the registry; this prevents a transient signing failure from leaving the release in a broken half-state where the image exists but no GitOps PR was opened.

```yaml
jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/build.yml@v1.28.5
    with:
      enable_cosign_sign: true
      cosign_max_attempts: 5
      cosign_initial_delay: 15
      continue_gitops_on_signing_failure: true
    secrets: inherit
```

When continuation kicks in, the workflow:

- Logs a `::warning::` with the unsigned digest
- Writes a "manual action required" block to the GitHub Actions step summary listing the digest and image refs
- Lets the `dispatch-helm` / GitOps job proceed normally

**Manual recovery** — sign the digest after the fact, then verify:

```bash
cosign sign --yes <registry>/<org>/<app>@<sha256-digest>
cosign verify --certificate-identity-regexp '...' --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' <ref>
```

Treat any release with a "Unsigned image" summary block as **not production-ready** until the manual sign step is completed.

### Verifying signatures

```bash
cosign verify \
  --certificate-identity-regexp="^https://github\.com/LerianStudio/.+/.github/workflows/.+@refs/(heads|tags)/.+$" \
  --certificate-oidc-issuer="https://token.actions.githubusercontent.com" \
  docker.io/lerianstudio/my-app@sha256:abc123...
```

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

**Solution**: ARM64 builds only run on release tags by default. Beta/RC tags build amd64 only for faster CI. If you need ARM64 on beta/rc, use `force_multiplatform: true` and be aware of the longer build times.

## Related Workflows

- [GitOps Update](gitops-update-workflow.md) - Update deployments after build
- [Release](release-workflow.md) - Create releases that trigger builds
- [Slack Notify](slack-notify-workflow.md) - Notification system

---

**Last Updated:** 2025-12-09
**Version:** 1.0.0
