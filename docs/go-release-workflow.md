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
| `app_name_prefix` | Prefix for app names in monorepo (e.g. `midaz` -> `midaz-agent`) | string | `''` |
| `app_name_overrides` | Explicit `path:name` app name mappings | string | `''` |
| `dockerhub_org` | DockerHub organization name | string | `lerianstudio` |
| `path_level` | Directory depth level to extract app name | string | `2` |
| `build_context_from_working_dir` | Use the component working_dir as Docker build context | boolean | `false` |
| `enable_helm_dispatch` | Dispatch to the Helm repository for chart updates after build | boolean | `false` |
| `helm_chart` | Helm chart name to update (required when `enable_helm_dispatch`) | string | `''` |
| `helm_detect_env_changes` | Detect new environment variables for Helm during dispatch | boolean | `true` |
| `helm_values_key_mappings` | JSON mapping of component names to values.yaml keys | string | `''` |
| `enable_gitops_update` | Run the gitops-update job on tag push | boolean | `true` |
| `gitops_repository` | GitOps repository to update (org/repo) | string | `LerianStudio/midaz-firmino-gitops` |
| `gitops_artifact_pattern` | Pattern to download GitOps artifacts | string | `''` |
| `gitops_yaml_key_mappings` | JSON mapping of artifact names to YAML keys | string | `''` |
| `gitops_runner_type` | Runner for the gitops-update (deploy) job (needs cluster access) | string | `firmino-lxc-runners` |
| `enable_argocd_sync` | Trigger ArgoCD sync after updating the GitOps repo | boolean | `true` |
| `commit_message_prefix` | Prefix for the GitOps commit message (defaults to repo name when empty) | string | `''` |
| `deploy_in_firmino` | Force-off override for Firmino; set `false` to suppress deployment even when the manifest includes the app | boolean | `true` |
| `deploy_in_clotilde` | Force-off override for Clotilde; set `false` to suppress deployment even when the manifest includes the app | boolean | `true` |
| `use_dynamic_mapping` | Use dynamic artifact-to-YAML key mapping | boolean | `false` |
| `configmap_updates` | JSON mapping of artifact names to configmap keys (helmfile only) | string | `''` |
| `enable_docker_login` | Log in to DockerHub in the gitops-update job | boolean | `false` |
| `enable_apidog_e2e` | Run the ApiDog E2E test job on tag push after a successful gitops-update | boolean | `false` |
| `apidog_runner_type` | Runner for the ApiDog E2E test job (needs reach to the deployed environment) | string | `firmino-lxc-runners` |
| `apidog_auto_detect_environment` | Auto-detect the ApiDog environment from the tag (beta → dev, rc → stg); when `false`, uses `APIDOG_ENVIRONMENT_ID` | boolean | `true` |
| `shared_paths` | Path patterns that trigger a release/build for all components | string | `''` |
| `filter_paths` | Path prefixes to filter (empty = single-app repo) | string | `''` |

## Secrets

| Secret | Description | Required |
|--------|-------------|----------|
| `MANAGE_TOKEN` | Token for release commits, tags and private module access | No |
| `SLACK_WEBHOOK_URL` | Slack webhook for pipeline notifications | No |
| `HELM_REPO_TOKEN` | Token for dispatching Helm chart updates (when enabled in build) | No |
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

## ApiDog E2E tests

Set `enable_apidog_e2e: true` to run [api-dog-e2e-tests](./api-dog-e2e-tests-workflow.md) on tag push after a successful `update_gitops`. The job is skipped on branch pushes and when the gitops update did not succeed.

Because the underlying workflow expects fixed secret names (`test_scenario_id`, `apidog_access_token`, …), the ApiDog secrets **cannot** be passed via `secrets: inherit` — map them explicitly to the `APIDOG_*` secrets this workflow declares. With `apidog_auto_detect_environment: true` (default), the tag type selects the environment (`-beta.` → `APIDOG_DEV_ENVIRONMENT_ID`, `-rc.` → `APIDOG_STG_ENVIRONMENT_ID`); the underlying workflow errors on tags that are neither beta nor rc, so enable it only for repos that tag pre-release. For manual mode set `apidog_auto_detect_environment: false` and provide `APIDOG_ENVIRONMENT_ID`.

```yaml
jobs:
  pipeline:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-release.yml@v1
    with:
      enable_gitops_artifacts: true
      enable_apidog_e2e: true
    secrets:
      MANAGE_TOKEN: ${{ secrets.MANAGE_TOKEN }}
      SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
      APIDOG_TEST_SCENARIO_ID: ${{ secrets.MIDAZ_APIDOG_TEST_SCENARIO_ID }}
      APIDOG_ACCESS_TOKEN: ${{ secrets.APIDOG_ACCESS_TOKEN }}
      APIDOG_DEV_ENVIRONMENT_ID: ${{ secrets.MIDAZ_APIDOG_DEV_ENVIRONMENT_ID }}
      APIDOG_STG_ENVIRONMENT_ID: ${{ secrets.MIDAZ_APIDOG_STG_ENVIRONMENT_ID }}
```

## Permissions

The single caller job must grant the union of what the internal jobs need: `id-token: write`, `contents: write`, `packages: write`, `pull-requests: write`, `issues: write`.

## Related

- [release](./release-workflow.md) — semantic-release pipeline this umbrella calls
- [build](./build-workflow.md) — container build & push this umbrella calls
- [gitops-update](./gitops-update-workflow.md) — GitOps update this umbrella calls
- [api-dog-e2e-tests](./api-dog-e2e-tests-workflow.md) — optional post-gitops E2E tests this umbrella calls
- [go-pr-validation](./go-pr-validation.md) — the matching PR validation umbrella
