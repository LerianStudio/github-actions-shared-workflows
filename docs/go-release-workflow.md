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

### Repository layouts

`filter_paths` drives both the release matrix and the build matrix, which covers two layouts:

- **Single app** — `filter_paths` empty: one semantic-release tag, one image.
- **Per-component monorepo** — `filter_paths` set: each changed component gets its own release tag and its own image.

A third layout needs `release_single_app: true`: **one semantic-release tag for the whole repo, but one image per component**. Set `filter_paths` to the component prefixes (so the tag-push build still produces N images) and `release_single_app: true` so the branch-push release ignores `filter_paths` and runs once from the repo root. Without it, each component spawns a parallel `Semantic Release` job and they race to tag the same branch.

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
| `app_name` | Override app/image name (build single-app mode + gitops deploy name). Empty → gitops name derives from `app_name_prefix`, then repo name | string | `''` |
| `docker_build_args` | Newline-separated Docker build args | string | `''` |
| `enable_cosign_sign` | Sign images with cosign keyless (OIDC) | boolean | `true` |
| `app_name_prefix` | Prefix for app names in monorepo (e.g. `midaz` -> `midaz-agent`) | string | `''` |
| `app_name_overrides` | Explicit `path:name` app name mappings | string | `''` |
| `dockerhub_org` | DockerHub organization name | string | `lerianstudio` |
| `path_level` | Directory depth level to extract app name | string | `2` |
| `build_context_from_working_dir` | Use the component working_dir as Docker build context | boolean | `false` |
| `enable_helm_dispatch` | Dispatch to the Helm repository for chart updates after build | boolean | `false` |
| `helm_chart` | Helm chart name to update (required when `enable_helm_dispatch`) | string | `''` |
| `helm_detect_env_changes` | Detect new environment variables for Helm during dispatch | boolean | `true` |
| `helm_values_key_mappings` | JSON mapping of component names to values.yaml keys | string | `''` |
| `extra_builds` | JSON array of additional build groups, each forwarded to `build.yml` with its own config; all feed the single gitops-update (see [Multiple build groups](#multiple-build-groups)) | string | `''` |
| `enable_gitops_update` | Run the gitops-update job on tag push | boolean | `true` |
| `gitops_repository` | GitOps repository to update (org/repo) | string | `LerianStudio/midaz-firmino-gitops` |
| `gitops_artifact_pattern` | Pattern to download GitOps artifacts. Empty → `gitops-tags-<repo-name>*` | string | `''` |
| `gitops_yaml_key_mappings` | JSON mapping of artifact names to YAML keys | string | `''` |
| `gitops_runner_type` | Runner for the gitops-update (deploy) job (needs cluster access) | string | `eveo-lxc-runners` |
| `enable_argocd_sync` | Trigger ArgoCD sync after updating the GitOps repo | boolean | `true` |
| `commit_message_prefix` | Prefix for the GitOps commit message. Empty → `app_name_prefix`, then repo name | string | `''` |
| `deploy_in_firmino` | Force-off override for Firmino; set `false` to suppress deployment even when the manifest includes the app | boolean | `true` |
| `deploy_in_clotilde` | Force-off override for Clotilde; set `false` to suppress deployment even when the manifest includes the app | boolean | `true` |
| `use_dynamic_mapping` | Use dynamic artifact-to-YAML key mapping | boolean | `false` |
| `configmap_updates` | JSON mapping of artifact names to configmap keys (helmfile only) | string | `''` |
| `enable_docker_login` | Log in to DockerHub in the gitops-update job | boolean | `false` |
| `s3_uploads` | JSON array of S3 upload entries run after build on tag push (see [S3 migrations upload](#s3-migrations-upload)) | string | `''` |
| `enable_apidog_e2e` | Run the ApiDog E2E test job on tag push after a successful gitops-update | boolean | `false` |
| `apidog_runner_type` | Runner for the ApiDog E2E test job (needs reach to the deployed environment) | string | `eveo-lxc-runners` |
| `apidog_auto_detect_environment` | Auto-detect the ApiDog environment from the tag (beta → dev, rc → stg); when `false`, uses `APIDOG_ENVIRONMENT_ID` | boolean | `true` |
| `shared_paths` | Path patterns that trigger a release/build for all components | string | `''` |
| `filter_paths` | Path prefixes to filter (empty = single-app repo) | string | `''` |
| `release_single_app` | Force single-app mode for the release job even when `filter_paths` is set (one version tag, many images) | boolean | `false` |

> **Derived gitops defaults** — to slim down gitops/helm plugin callers, three gitops-update inputs derive from `app_name_prefix` / the repo name when left unset: `commit_message_prefix` → `app_name_prefix`; the gitops deploy `app_name` → `app_name_prefix`; `gitops_artifact_pattern` → `gitops-tags-<repo-name>*`. Set any of them explicitly to override (e.g. a repo whose deploy app name differs from its `app_name_prefix`, or a monorepo needing a different artifact suffix). All derivations fall back to the repository name when `app_name_prefix` is also empty, preserving the previous behavior.

## Secrets

| Secret | Description | Required |
|--------|-------------|----------|
| `MANAGE_TOKEN` | Token for release commits, tags and private module access | No |
| `SLACK_WEBHOOK_URL` | Slack webhook for pipeline notifications | No |
| `HELM_REPO_TOKEN` | Token for dispatching Helm chart updates (when enabled in build) | No |
| `AWS_MIGRATIONS_ROLE_ARN` | IAM role ARN assumed by the S3 upload job (required when `s3_uploads` is set) | No |
| `APIDOG_TEST_SCENARIO_ID` | ApiDog test scenario ID (required when `enable_apidog_e2e`) | No |
| `APIDOG_ACCESS_TOKEN` | ApiDog access token (required when `enable_apidog_e2e`) | No |
| `APIDOG_DEV_ENVIRONMENT_ID` | ApiDog dev environment ID (used for beta tags in auto-detect mode) | No |
| `APIDOG_STG_ENVIRONMENT_ID` | ApiDog staging environment ID (used for rc tags in auto-detect mode) | No |
| `APIDOG_ENVIRONMENT_ID` | ApiDog environment ID for manual mode (`apidog_auto_detect_environment: false`) | No |

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

## S3 migrations upload

Set `s3_uploads` to a JSON array to upload files (e.g. SQL migrations) to S3 on tag push, after `build` succeeds. All entries are processed sequentially inside a single `s3_upload` job (this avoids a GitHub Actions limitation where a `matrix` over a reusable-workflow `uses:` call is not instantiated in a nested reusable-workflow context), independent of the gitops update (it reads repo files, not build artifacts). Per-entry keys: `s3_bucket` (required), `file_pattern` (required), `s3_prefix` (optional), `strip_prefix` (optional — removes that prefix from the source path so keys land under `s3_prefix` directly), `flatten` (optional, defaults to `true`; set `false` to preserve the directory structure), and `aws_role_arn` (optional — see per-entry role below). The target environment folder is auto-detected from the tag (`-beta` → development, `-rc` → staging, `vX.Y.Z` → production).

By default the job assumes the `AWS_MIGRATIONS_ROLE_ARN` secret via OIDC (region `us-east-2`); map it explicitly in the caller.

### Per-entry IAM role

To upload to buckets that require different IAM roles, set `aws_role_arn` on an entry to the **role ARN value** — resolve the secret in the caller and inline it into the JSON (GitHub Actions cannot look up a secret by a dynamic name). Entries with `aws_role_arn` assume that role via OIDC for their upload; entries without it use the default `AWS_MIGRATIONS_ROLE_ARN`. Each role referenced this way must have an OIDC trust policy that allows the **caller** repository (same prerequisite as the default role).

```yaml
secrets:
  AWS_MIGRATIONS_ROLE_ARN: ${{ secrets.AWS_MIGRATIONS_ROLE_ARN }}
with:
  s3_uploads: |
    [
      { "s3_bucket": "lerian-migration-files", "file_pattern": "migrations/*.sql", "s3_prefix": "myapp/postgresql" },
      { "s3_bucket": "lerian-casdoor-init-data", "file_pattern": "init/casdoor/*.json", "aws_role_arn": "${{ secrets.AWS_INIT_DATA_ROLE_ARN }}" }
    ]
```
## ApiDog E2E tests

Set `enable_apidog_e2e: true` to run [api-dog-e2e-tests](./api-dog-e2e-tests-workflow.md) on tag push after a successful `update_gitops`. The job is skipped on branch pushes and when the gitops update did not succeed.

Because the underlying workflow expects fixed secret names (`test_scenario_id`, `apidog_access_token`, …), the ApiDog secrets **cannot** be passed via `secrets: inherit` — map them explicitly to the `APIDOG_*` secrets this workflow declares. With `apidog_auto_detect_environment: true` (default), the tag type selects the environment (`-beta.` → `APIDOG_DEV_ENVIRONMENT_ID`, `-rc.` → `APIDOG_STG_ENVIRONMENT_ID`); the underlying workflow errors on tags that are neither beta nor rc, so enable it only for repos that tag pre-release. For manual mode set `apidog_auto_detect_environment: false` and provide `APIDOG_ENVIRONMENT_ID`.
## Multiple build groups

By default `go-release` runs **one** `build.yml` call (driven by the top-level `filter_paths`/`app_name_*`/`build_context_from_working_dir` inputs) before the single `update_gitops`. Some repos ship images that need **different build configs in the same release** — e.g. an app + workers built from the repo root, plus a tool/mock image built with `build_context_from_working_dir: true`. These cannot be merged into one `build.yml` call.

Set `extra_builds` to a JSON array of build groups. Each group runs a parallel `build.yml` matrix leg alongside the primary build, and every group uploads its GitOps tag artifacts into the same run, so the single `update_gitops` aggregates all of them. Per-group keys (all optional except `filter_paths`): `filter_paths`, `shared_paths`, `path_level`, `normalize_to_filter` (defaults to `true`; set `false` to disable normalizing changed paths to their filter path), `app_name`, `app_name_prefix`, `app_name_overrides`, `build_context_from_working_dir`, `docker_build_args`, `enable_gitops_artifacts` (defaults to `true`), `enable_helm_dispatch`, `helm_chart`, `helm_detect_env_changes`, `helm_values_key_mappings`. Registry/cosign/runner settings are inherited from the top-level inputs.

> **Important** — `update_gitops` downloads artifacts by `gitops_artifact_pattern` (default `gitops-tags-<repo-name>*`). When an extra build produces an image whose name does **not** start with the repo name (e.g. `mock-btg-server`), set `gitops_artifact_pattern` to a wildcard that captures every image (e.g. `gitops-tags-*`), otherwise that image's tag artifact is skipped.

```yaml
jobs:
  pipeline:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-release.yml@v1
    with:
      enable_gitops_artifacts: true
      s3_uploads: |
        [
          {
            "s3_bucket": "lerian-migration-files",
            "file_pattern": "components/ledger/migrations/onboarding/*.sql",
            "s3_prefix": "ledger/onboarding/postgresql"
          },
          {
            "s3_bucket": "lerian-migration-files",
            "file_pattern": "components/ledger/migrations/transaction/*.sql",
            "s3_prefix": "ledger/transaction/postgresql",
            "strip_prefix": "components/ledger/migrations/transaction",
            "flatten": false
          }
        ]
    secrets:
      MANAGE_TOKEN: ${{ secrets.MANAGE_TOKEN }}
      AWS_MIGRATIONS_ROLE_ARN: ${{ secrets.AWS_MIGRATIONS_ROLE_ARN }}
      enable_apidog_e2e: true
    secrets:
      MANAGE_TOKEN: ${{ secrets.MANAGE_TOKEN }}
      SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
      APIDOG_TEST_SCENARIO_ID: ${{ secrets.MIDAZ_APIDOG_TEST_SCENARIO_ID }}
      APIDOG_ACCESS_TOKEN: ${{ secrets.APIDOG_ACCESS_TOKEN }}
      APIDOG_DEV_ENVIRONMENT_ID: ${{ secrets.MIDAZ_APIDOG_DEV_ENVIRONMENT_ID }}
      APIDOG_STG_ENVIRONMENT_ID: ${{ secrets.MIDAZ_APIDOG_STG_ENVIRONMENT_ID }}
      # Primary build — app + 3 workers from the repo root
      filter_paths: |
        components/application
        components/worker/webhook/inbound
        components/worker/webhook/outbound
        components/worker/reconciliation
      path_level: '4'
      app_name_prefix: "plugin-br-pix-indirect-btg"
      app_name_overrides: |
        components/application:
        components/worker/webhook/inbound:worker-inbound
        components/worker/webhook/outbound:worker-outbound
        components/worker/reconciliation:worker-reconciliation
      enable_gitops_artifacts: true
      # Extra build — mock server with its own build context
      extra_builds: |
        [
          {
            "filter_paths": "tools/mock-btg-server",
            "path_level": "2",
            "app_name_overrides": "tools/mock-btg-server:mock-btg-server",
            "build_context_from_working_dir": true
          }
        ]
      # Wildcard so the mock image's artifact is also picked up
      gitops_artifact_pattern: "gitops-tags-*"
      gitops_yaml_key_mappings: '{"plugin-br-pix-indirect-btg.tag": ".pix.image.tag", "worker-inbound.tag": ".inbound.image.tag", "worker-outbound.tag": ".outbound.image.tag", "worker-reconciliation.tag": ".reconciliation.image.tag", "mock-btg-server.tag": ".mock.image.tag"}'
    secrets: inherit
```

## Permissions

The single caller job must grant the union of what the internal jobs need: `id-token: write`, `contents: write`, `packages: write`, `pull-requests: write`, `issues: write`.

## Related

- [release](./release-workflow.md) — semantic-release pipeline this umbrella calls
- [build](./build-workflow.md) — container build & push this umbrella calls
- [gitops-update](./gitops-update-workflow.md) — GitOps update this umbrella calls
- [s3-upload](./s3-upload.md) — standalone S3 upload reusable workflow (the umbrella performs the equivalent upload inline via `s3_uploads`)
- [api-dog-e2e-tests](./api-dog-e2e-tests-workflow.md) — optional post-gitops E2E tests this umbrella calls
- [go-pr-validation](./go-pr-validation.md) — the matching PR validation umbrella
