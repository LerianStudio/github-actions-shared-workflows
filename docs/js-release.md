<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>js-release</h1></td>
  </tr>
</table>

Umbrella reusable workflow for JavaScript/TypeScript **service** repositories (deployable apps that ship as container images). A caller references this single workflow and it drives the full release pipeline, branching on the pushed ref:

- **Branch push** → change gate (`src/config/non-doc-changes`) → semantic release (`release.yml`). Documentation-only pushes skip the release.
- **Tag push** → container build & push (`typescript-build.yml`) → GitOps update (`gitops-update.yml`), gated on the build actually producing images.

Mirrors the [`go-release`](./go-release.md) umbrella for Go services — providing the same single-caller DX for Next.js frontends, NestJS backends, and any JS/TS service that ships a Docker image.

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
| `release_runner_type` | Optional runner override for the Release (publish) jobs only (forwarded to release.yml as `publish_runner_type`); empty falls back to `vars.GENERAL_RUNNERS`, then `runner_type` | string | `''` |
| `dry_run` | Run semantic-release and build in dry-run mode (no tags/releases/images created); also skips the E2E test job entirely | boolean | `false` |
| `ignore_globs` | Space-separated globs treated as docs/meta for the branch-push gate | string | `*.md docs/* .github/* LICENSE* .gitignore` |
| `semantic_version` | semantic-release version | string | `23.0.8` |
| `filter_paths` | Path prefixes to filter (empty = single-app repo) | string | `''` |
| `shared_paths` | Path patterns that trigger a release/build for all components | string | `''` |
| `path_level` | Directory depth level to extract app name | string | `2` |
| `enable_release_announcement` | Announce the published release to the repository Slack channel (see [release-workflow](release.md#release-announcement)) | boolean | `true` |
| `announcement_product_name` | Product name displayed in the announcement. Empty → repository name | string | `''` |
| `announcement_slack_channel` | Slack channel for the announcement. Empty → `RELEASE_SLACK_CHANNEL` repository variable; skipped when both are empty | string | `''` |
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
| `beta_environments` | Space-separated environments updated by a beta release (`develop` branch) | string | `dev` |
| `rc_environments` | Space-separated environments updated by an rc release (`release-candidate` branch) | string | `stg` |
| `stable_environments` | Space-separated environments updated by a stable release (`main` branch). Default `prd` so a hotfix does not overwrite features still in dev/stg. Set to `dev stg prd` to refresh lower environments too. Sandbox is controlled separately by `update_sandbox` | string | `prd` |
| `gitops_app_name` | App name used **only** by `update_gitops` (deployment-matrix lookup + the `applications/{env}/{app}/values.yaml` path). Empty → the existing chain (`app_name_prefix`, then the repo name) | string | `''` |
| `gitops_artifact_pattern` | Pattern to download GitOps artifacts. Empty → `gitops-tags-<repo-name>*` | string | `''` |
| `gitops_yaml_key_mappings` | JSON mapping of artifact names to YAML keys | string | `''` |
| `deployment_matrix_ref` | Git ref of shared-workflows to read the deployment matrix from | string | `main` |
| `enable_argocd_sync` | Trigger ArgoCD sync after updating the GitOps repo | boolean | `true` |
| `commit_message_prefix` | Prefix for the GitOps commit message. Empty → `app_name_prefix`, then repo name | string | `''` |
| `use_dynamic_mapping` | Use dynamic artifact-to-YAML key mapping | boolean | `false` |
| `configmap_updates` | JSON mapping of artifact names to configmap keys (helmfile only) | string | `''` |
| `enable_docker_login` | Log in to DockerHub in the gitops-update job | boolean | `false` |
| `enable_e2e` | Enable the E2E test job after the build (tag push only) | boolean | `false` |
| `e2e_script` | npm script for E2E tests (e.g. `test:e2e`, `test:e2e:mock`) | string | `test:e2e` |
| `e2e_base_url` | Base URL injected as `BASE_URL` env var. Empty = localhost fallback | string | `''` |
| `node_version` | Node.js version for the E2E runner | string | `22` |
| `e2e_runner_type` | Optional runner override for the E2E Tests job only; empty falls back to `runner_type` | string | `''` |
| `e2e_s3_artifact_path` | Subpath under `s3://lerian-e2e-artifacts/<repo>/<channel>/<tag>/` where the Playwright report is uploaded. Channel (`main`/`beta`/`rc`) is derived from the tag's prerelease identifier. Only used when `AWS_E2E_ARTIFACTS_ROLE_ARN` is set | string | `playwright-report` |
| `enable_ungoliant_release_diff` | Fire the Ungoliant release-diff webhook on tag push after a successful gitops-update (see [Ungoliant release diff](#ungoliant-release-diff)) | boolean | `false` |
| `ungoliant_app` | App slug sent to the controller; when empty falls back to `app_name_prefix`, then the repo name | string | `''` |
| `ungoliant_env_type` | **Deprecated no-op** — the app's registration decides the surface | string | `chaos` |
| `ungoliant_tenancy` | **Deprecated no-op** — the app's registration decides the surface | string | `st` |
| `ungoliant_controller_url` | Ungoliant controller base URL (reachable over Tailscale) | string | `https://ungoliant-controller.anacleto.lerian.net` |
| `ungoliant_runner_type` | Runner for the Ungoliant release-diff job (needs Tailscale reach to the controller) | string | `eveo-anacleto-lxc-runners` |

## Secrets

| Secret | Description | Required |
|--------|-------------|----------|
| `MANAGE_TOKEN` | Token for release commits, tags and private module access | No |
| `SLACK_WEBHOOK_URL` | Slack webhook for pipeline notifications | No |
| `NPM_TOKEN` | npm registry auth token, forwarded to the `release` job. Only needed when the caller's own `.releaserc` includes `@semantic-release/npm` (a component with independent semver that publishes to an npm registry) | No |
| `AWS_E2E_ARTIFACTS_ROLE_ARN` | IAM role ARN assumed via OIDC to upload the Playwright report to the `lerian-e2e-artifacts` S3 bucket (`s3://lerian-e2e-artifacts/<repo>/<channel>/<tag>/<e2e_s3_artifact_path>/`). Unset → S3 upload step is skipped, only the GitHub Actions artifact is produced | No |
| `UNGOLIANT_WEBHOOK_TOKEN` | Token sent as the `X-Ungoliant-Token` header (used when `enable_ungoliant_release_diff`) | No |

All other secrets required by the underlying primitives (GitHub App tokens, GPG key, DockerHub credentials, etc.) are forwarded automatically via `secrets: inherit`.

## Outputs

| Output | Description |
|--------|-------------|
| `has_e2e_s3_upload` | Whether the E2E Playwright report was uploaded to the `lerian-e2e-artifacts` S3 bucket (`true`/`false`). Always `false` when `AWS_E2E_ARTIFACTS_ROLE_ARN` is unset or `enable_e2e` is `false`. |

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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/js-release.yml@tier-1
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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/js-release.yml@tier-1
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

### E2E tests on tag push — mock mode

Self-contained: no real backend required. Playwright spins up its own mock server.

```yaml
jobs:
  pipeline:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/js-release.yml@tier-1
    with:
      enable_ghcr: true
      enable_e2e: true
      e2e_script: test:e2e:mock
    secrets: inherit
```

### E2E tests on tag push — real environment mode

Runs against a deployed staging URL injected via `BASE_URL`.

```yaml
jobs:
  pipeline:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/js-release.yml@tier-1
    with:
      enable_ghcr: true
      enable_e2e: true
      e2e_script: test:e2e
      e2e_base_url: ${{ vars.STAGING_URL }}
    secrets: inherit
```

> The consumer's `playwright.config.ts` should read `process.env.BASE_URL || 'http://localhost:8081'` to support both modes.

### Uploading the E2E report to S3

When the `AWS_E2E_ARTIFACTS_ROLE_ARN` secret is available (via `secrets: inherit` from an org-level secret, or passed explicitly), the Playwright report is also uploaded to the `lerian-e2e-artifacts` S3 bucket under a path that mirrors the caller repository, release channel, and release tag:

```
s3://lerian-e2e-artifacts/<repo-name>/<channel>/<tag>/<e2e_s3_artifact_path>/
```

`<channel>` is derived from the tag's prerelease identifier (which mirrors the branch that cut the release per `.releaserc.yml`): `develop` → `vX.Y.Z-beta.N` → `beta`, `release-candidate` → `vX.Y.Z-rc.N` → `rc`, `main` → plain `vX.Y.Z` → `main`.

Example for `product-console` releasing `v1.10.0-beta.5` (cut from `develop`) with the default `e2e_s3_artifact_path`:

```
s3://lerian-e2e-artifacts/product-console/beta/v1.10.0-beta.5/playwright-report/
```

```yaml
jobs:
  pipeline:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/js-release.yml@tier-1
    with:
      enable_ghcr: true
      enable_e2e: true
      e2e_script: test:e2e:mock
      # e2e_s3_artifact_path: playwright-report  # optional override
    secrets: inherit
```

No caller changes are needed once the `AWS_E2E_ARTIFACTS_ROLE_ARN` org secret is configured — `secrets: inherit` picks it up automatically. When the secret is not set, the S3 upload step is skipped and the workflow behaves exactly as before (GitHub Actions artifact only).

### Replacing two caller files with one

Before — two workflow files in the caller repo:

```yaml
# release.yml
jobs:
  release:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/typescript-release.yml@tier-1
    secrets: inherit

# build.yml
jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/typescript-build.yml@tier-1
    with:
      enable_ghcr: true
      enable_gitops_artifacts: true
    secrets: inherit

  gitops:
    needs: build
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@tier-1
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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/js-release.yml@tier-1
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

## Ungoliant release diff

Set `enable_ungoliant_release_diff: true` to fire the Ungoliant controller `release-diff` webhook on tag push, **only after a successful `update_gitops`** (i.e. the release was actually deployed). The job resolves the diff for the tag and POSTs it to the controller, which triggers chaos/fuzz analysis, using the [ungoliant-release-diff](../src/validate/ungoliant-release-diff/README.md) composite.

The controller is reachable only over Tailscale, so the job runs on the `eveo-anacleto-lxc-runners` self-hosted runner by default (`ungoliant_runner_type`). Inputs are derived automatically:

- **app** — `ungoliant_app`, else `app_name_prefix`, else the repo name.
- **version** — the pushed tag (`github.ref_name`).
- **release channel** — read from the tag, which maps 1:1 to the source branch: `-rc*` → `rc` (release-candidate), `-beta*`/`-alpha*` → `beta` (develop), a bare semver version → `stable` (main). A tag that carries no channel marker and is not a bare semver (`build-1234`, `nightly`, `v1.2.3.4`) **fails the job** instead of being guessed at — the old fallback sent anything unrecognised to the `stable`/production channel, which is the most consequential direction and the one nobody wants by accident.

**Where the release is validated is not a workflow input.** The channel picks the cluster (`beta`→dev, `rc`→stg, `stable`→prd) and the tenancy registered in the console's Applications tab picks the rest. `ungoliant_env_type` and `ungoliant_tenancy` are **deprecated no-ops**: they used to compose a `target_env` that the controller honours *over* its own configuration, and since they default to `chaos`/`st` every release silently overrode its own registration — an app registered for stg ran against dev without a word. They are still accepted so no caller breaks. An app with no registration for the channel is refused, which is the configuration doing its job.

Provide `UNGOLIANT_WEBHOOK_TOKEN` via `secrets: inherit` for an authenticated call.

```yaml
jobs:
  pipeline:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/js-release.yml@tier-1
    with:
      enable_ungoliant_release_diff: true
    secrets: inherit
```

## Related

- [release](./release.md) — semantic-release pipeline this umbrella calls on branch push
- [typescript-build](./typescript-build.md) — container build & push this umbrella calls
- [gitops-update](./gitops-update.md) — GitOps update this umbrella calls
- [go-release](./go-release.md) — the equivalent umbrella for Go service repositories
- [ungoliant-release-diff](../src/validate/ungoliant-release-diff/README.md) — the composite the release-diff job runs
