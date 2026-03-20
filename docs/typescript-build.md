<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>typescript-build</h1></td>
  </tr>
</table>

Reusable workflow for building and pushing Docker images from TypeScript/Node.js projects. Provides built-in `npmrc` authentication for GitHub Packages private `@lerianstudio` dependencies.

The build logic is encapsulated in the [`docker-build-ts`](../src/build/docker-build-ts/) composite action.

## Why Use This Instead of `build.yml`?

| Feature | `build.yml` | `typescript-build.yml` |
|---------|-------------|------------------------|
| Default registry | DockerHub | GHCR |
| `npmrc` secret | Not included | Always injected automatically |
| `build_secrets` behavior | Replaces all secrets | Additive (extra secrets on top of npmrc) |
| `dry_run` mode | Not available | Available |
| `workflow_dispatch` | Not available | Available for manual testing |
| Dockerfile per component | Uses `dockerfile_name` only | Resolves `matrix.app.dockerfile` with fallback |

## Usage

### Basic Example (Single App)

```yaml
name: Build Pipeline
on:
  push:
    tags:
      - 'v*.*.*-beta.*'
      - 'v*.*.*-rc.*'
      - 'v[0-9]+.[0-9]+.[0-9]+'

permissions:
  contents: read
  packages: write

jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/typescript-build.yml@v1.0.0
    secrets: inherit
```

### Multi-Component with Custom Dockerfiles

```yaml
jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/typescript-build.yml@v1.0.0
    with:
      runner_type: firmino-lxc-runners
      components_json: |
        [
          {"name":"my-app","working_dir":".","dockerfile":"docker-app.Dockerfile"},
          {"name":"my-app-job","working_dir":".","dockerfile":"docker-job.Dockerfile"}
        ]
    secrets: inherit
```

### With Helm Dispatch

```yaml
jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/typescript-build.yml@v1.0.0
    with:
      components_json: '[{"name":"my-app","working_dir":".","dockerfile":"docker-app.Dockerfile"}]'
      enable_helm_dispatch: true
      helm_chart: my-app
      helm_target_ref: develop
      helm_values_key_mappings: '{"my-app":"api"}'
    secrets: inherit
```

### With Additional Build Secrets

```yaml
jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/typescript-build.yml@v1.0.0
    with:
      build_secrets: |
        custom_token=${{ secrets.CUSTOM_TOKEN }}
    secrets: inherit
```

The `npmrc` secret is always injected automatically. `build_secrets` adds extra secrets on top of it.

### Dry-Run Mode (Safe Testing)

```yaml
jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/typescript-build.yml@v1.0.0
    with:
      dry_run: true
      components_json: '[{"name":"my-app","working_dir":".","dockerfile":"Dockerfile"}]'
    secrets: inherit
```

Builds the Docker image without pushing. Useful for validating Dockerfiles and build secrets.

### Monorepo with Change Detection

```yaml
jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/typescript-build.yml@v1.0.0
    with:
      filter_paths: |
        apps/api
        apps/worker
      path_level: "2"
      app_name_prefix: "my-project"
    secrets: inherit
```

## Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `runner_type` | string | `blacksmith-4vcpu-ubuntu-2404` | Runner to use |
| `dry_run` | boolean | `false` | Preview changes without pushing images |
| `filter_paths` | string | `''` | Path prefixes for monorepo change detection |
| `path_level` | string | `2` | Limits the path to the first N segments |
| `enable_dockerhub` | boolean | `false` | Enable pushing to DockerHub |
| `enable_ghcr` | boolean | `true` | Enable pushing to GHCR |
| `dockerhub_org` | string | `lerianstudio` | DockerHub organization name |
| `ghcr_org` | string | `''` | GHCR organization name (defaults to repo owner) |
| `dockerfile_name` | string | `Dockerfile` | Default Dockerfile name (overridden by `matrix.app.dockerfile`) |
| `app_name_prefix` | string | `''` | Prefix for app names in monorepo |
| `app_name_overrides` | string | `''` | Explicit app name mappings |
| `build_context` | string | `.` | Docker build context |
| `build_secrets` | string | `''` | Additional secrets (npmrc is always included) |
| `enable_gitops_artifacts` | boolean | `false` | Enable GitOps artifacts upload |
| `components_json` | string | `''` | Explicit JSON array of components to build |
| `normalize_to_filter` | boolean | `true` | Normalize changed paths to filter path |
| `enable_helm_dispatch` | boolean | `false` | Enable Helm repository dispatch |
| `helm_repository` | string | `LerianStudio/helm` | Helm repository (org/repo) |
| `helm_chart` | string | `''` | Helm chart name to update |
| `helm_target_ref` | string | `main` | Target branch in Helm repository |
| `helm_components_base_path` | string | `components` | Base path for components |
| `helm_env_file` | string | `.env.example` | Env example file name |
| `helm_detect_env_changes` | boolean | `true` | Detect new env variables for Helm |
| `helm_dispatch_on_rc` | boolean | `false` | Enable Helm dispatch for rc tags |
| `helm_dispatch_on_beta` | boolean | `false` | Enable Helm dispatch for beta tags |
| `helm_values_key_mappings` | string | `''` | Component names to values.yaml keys mapping |

## Secrets

| Secret | Required | Description |
|--------|----------|-------------|
| `MANAGE_TOKEN` | Yes | GitHub token for GHCR login and npmrc authentication |
| `DOCKER_USERNAME` | If DockerHub enabled | DockerHub username |
| `DOCKER_PASSWORD` | If DockerHub enabled | DockerHub password |
| `HELM_REPO_TOKEN` | If Helm dispatch enabled | Token with access to Helm repository |
| `SLACK_WEBHOOK_URL` | No | Slack webhook for build notifications |

## Architecture

```
typescript-build.yml (reusable workflow)
  ├── prepare job          → matrix, platforms, version
  ├── build job            → calls src/build/docker-build-ts composite
  ├── notify job           → calls slack-notify.yml
  └── dispatch-helm job    → calls dispatch-helm.yml
```

## Jobs

### prepare

Determines the build matrix and platform strategy:
- **Single app mode** (default): builds from repository root
- **Explicit components mode**: uses `components_json` directly
- **Monorepo mode**: detects changed paths via `filter_paths`
- **Platform strategy**: `linux/amd64` for beta/rc, `linux/amd64,linux/arm64` for releases

### build

Runs the `docker-build-ts` composite for each component in the matrix. Also handles GitOps artifact creation when enabled.

### notify

Sends Slack notification with build status. Skipped during dry run.

### dispatch-helm

Dispatches to Helm repository for chart updates. Only runs on successful non-dry-run builds.

## Dockerfile Requirements

Dockerfiles must mount the `npmrc` secret for installing private packages:

```dockerfile
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc npm install
```

## Related Workflows

- [`build.yml`](build.md) — Generic Docker build workflow (Go-oriented defaults)
- [`typescript-ci.yml`](typescript-ci.md) — TypeScript continuous integration
- [`typescript-release.yml`](typescript-release-workflow.md) — TypeScript semantic release
- [`src/build/docker-build-ts`](../src/build/docker-build-ts/) — Composite action used by this workflow

---

**Last Updated:** 2026-03-09
**Version:** 1.0.0
