# GitOps Update Workflow

Reusable workflow for updating GitOps repository with new image tags across multiple servers and environments.

## Features

- **Manifest-driven topology**: Cluster membership per app is declared in [`config/deployment-matrix.yml`](../config/deployment-matrix.yml) — no caller-side configuration required to add a cluster to an existing app
- **Multi-server deployment**: Deploy to Firmino, Clotilde and/or Anacleto with dynamic path generation
- **Force-off overrides**: `deploy_in_<cluster>` inputs can suppress a cluster declared in the manifest, useful for emergency containment without editing the manifest
- **Convention-based configuration**: Auto-generates paths, names, and patterns from repository name
- **Multi-environment support**: dev (beta), stg (rc), prd (production), sandbox
- **Production sync**: Production releases automatically update all environments (dev, stg, prd, sandbox) on all servers
- **File existence validation**: Graceful handling of missing values files with warnings (never fails)
- **Flexible tag mapping**: Static or dynamic YAML key mapping
- **Automatic environment detection**: Based on git tag suffix
- **ArgoCD integration**: Automatic sync for each server/environment combination where files were updated
- **App existence check**: Verifies ArgoCD app exists before attempting sync
- **Docker Hub login**: Enabled by default to avoid rate limits
- **Customizable runners**: Support for different GitHub runner types

## Usage

### Minimal Example (Manifest-Driven)

```yaml
update_gitops:
  needs: build_backend
  if: needs.build_backend.result == 'success'
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@v1.0.0
  with:
    yaml_key_mappings: '{"backend.tag": ".auth.image.tag"}'
  secrets: inherit
```

> **Required Secrets**: `MANAGE_TOKEN`, `LERIAN_CI_CD_USER_NAME`, `LERIAN_CI_CD_USER_EMAIL`, `ARGOCD_GHUSER_TOKEN`, `ARGOCD_URL`, `DOCKER_USERNAME`, `DOCKER_PASSWORD`

The workflow reads `config/deployment-matrix.yml` from the shared-workflows repo (by default from `main`, override via `deployment_matrix_ref`) and resolves the cluster set automatically based on `app_name`. No `deploy_in_*` inputs are required for the common case.

**Auto-generated values** (for repo `my-backend-service`):
- App name: `my-backend-service` (must be present in the deployment matrix)
- Artifact pattern: `gitops-tags-my-backend-service-*`
- GitOps paths (one per cluster declared in the manifest):
  - `gitops/environments/<cluster>/helmfile/applications/{env}/my-backend-service/values.yaml`
- ArgoCD apps: `<cluster>-my-backend-service-{env}` for every resolved cluster
- Commit prefix: `my-backend-service`

### Force-Off Example (Skip Anacleto for One Run)

Useful when you need to ship a hotfix to Firmino and Clotilde but skip Anacleto temporarily (e.g., maintenance window) without touching the manifest:

```yaml
update_gitops:
  needs: build_backend
  if: needs.build_backend.result == 'success'
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@v1.0.0
  with:
    deploy_in_anacleto: false
    yaml_key_mappings: '{"backend.tag": ".auth.image.tag"}'
  secrets: inherit
```

`deploy_in_<cluster>` inputs only **subtract** clusters from the resolved set — they cannot add a cluster the manifest does not list.

### Multi-Component Example (Midaz)

```yaml
update_gitops:
  needs: build
  if: needs.build.result == 'success'
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@v1.0.0
  with:
    app_name: "midaz"
    artifact_pattern: "gitops-tags-midaz-*"
    yaml_key_mappings: '{"midaz-onboarding.tag": ".onboarding.image.tag", "midaz-transaction.tag": ".transaction.image.tag"}'
    commit_message_prefix: "midaz"
  secrets: inherit
```

## Inputs

### Required Inputs

| Input | Description | Example |
|-------|-------------|---------|
| `yaml_key_mappings` | JSON object mapping artifact names to YAML keys | `{"backend.tag": ".auth.image.tag"}` |

### Optional Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `gitops_repository` | string | `LerianStudio/midaz-firmino-gitops` | GitOps repository to update |
| `app_name` | string | (repo name) | Application name (auto-detected from repository) |
| `deploy_in_firmino` | boolean | `true` | Force-off override for Firmino (`false` = subtract from manifest-resolved set) |
| `deploy_in_clotilde` | boolean | `true` | Force-off override for Clotilde (`false` = subtract from manifest-resolved set) |
| `deploy_in_anacleto` | boolean | `true` | Force-off override for Anacleto (`false` = subtract from manifest-resolved set) |
| `deployment_matrix_file` | string | `config/deployment-matrix.yml` | Path to the deployment matrix manifest within the shared-workflows checkout |
| `deployment_matrix_ref` | string | `main` | Git ref of `LerianStudio/github-actions-shared-workflows` to read the deployment matrix from. Default `main` ensures all callers see manifest updates immediately, regardless of the workflow ref they pin. Override only when testing a branch. |
| `artifact_pattern` | string | `gitops-tags-{app}-*` | Pattern to download artifacts (auto-generated) |
| `commit_message_prefix` | string | (repo name) | Prefix for commit message (auto-generated) |
| `runner_type` | string | `blacksmith-4vcpu-ubuntu-2404` | GitHub runner type |
| `enable_argocd_sync` | boolean | `true` | Enable ArgoCD sync |
| `use_dynamic_mapping` | boolean | `false` | Use dynamic mapping for multiple components |
| `yq_version` | string | `v4.44.3` | Version of yq to install |
| `enable_docker_login` | boolean | `true` | Enable Docker Hub login to avoid rate limits |
| `configmap_updates` | string | - | JSON object mapping artifact names to configmap keys |

## Secrets

### Required Secrets

| Secret | Description |
|--------|-------------|
| `MANAGE_TOKEN` | GitHub token with access to GitOps repository |
| `LERIAN_CI_CD_USER_NAME` | Git user name for commits |
| `LERIAN_CI_CD_USER_EMAIL` | Git user email for commits |
| `LERIAN_CI_CD_USER_GPG_KEY` | GPG key for signing commits |
| `LERIAN_CI_CD_USER_GPG_KEY_PASSWORD` | GPG key passphrase |

### Required Secrets (ArgoCD)

| Secret | Description |
|--------|-------------|
| `ARGOCD_GHUSER_TOKEN` | ArgoCD authentication token |
| `ARGOCD_URL` | ArgoCD server URL |

### Required Secrets (Docker Hub)

| Secret | Description |
|--------|-------------|
| `DOCKER_USERNAME` | Docker Hub username (to avoid rate limits) |
| `DOCKER_PASSWORD` | Docker Hub password |

## Deployment Matrix

The workflow's cluster topology is declared in [`config/deployment-matrix.yml`](../config/deployment-matrix.yml) — a single source of truth maintained in this repo.

### How it works

1. The caller invokes the workflow at a pinned ref (e.g. `@v1.24.0`).
2. The workflow checks out the deployment matrix from `main` (or from the ref supplied via `deployment_matrix_ref`) — sparse checkout of the manifest file only. This decoupling lets manifest updates propagate to every caller without bumping the pinned workflow tag.
3. For the caller's `app_name`, the workflow collects every cluster whose `apps:` list contains it.
4. `deploy_in_<cluster>` inputs are applied as **force-off** overrides on the resolved set.
5. The remaining cluster set drives both the GitOps file updates and the ArgoCD sync matrix.

### Anatomy of the manifest

```yaml
version: 1

apps:
  registry:
    - midaz
    - plugin-fees
    # ... every app that uses this workflow

clusters:
  firmino:
    apps: [midaz, plugin-fees, ...]
  clotilde:
    apps: [midaz, plugin-fees, ...]
  anacleto:
    apps: [midaz, ...]
```

- `apps.registry` is the set of legal app names — typo gate.
- Each `clusters.<name>.apps` is an explicit list of which apps this cluster hosts.
- A cluster is added by appending one block. A cluster is removed by deleting it. Affects only this repo — caller workflows are untouched.

### Adding a new app to a cluster

1. Open a PR in this repo editing `config/deployment-matrix.yml`:
   - Add the app name to `apps.registry` (if new).
   - Add the app name to `clusters.<target>.apps`.
2. The `deployment-matrix` lint job validates schema, integrity, and duplicates on the PR.
3. Once merged, callers consuming the new ref (via Renovate/Dependabot or manual bump) automatically include the cluster on their next release — zero change required in caller repos.

### Adding a new cluster

1. Create `environments/<cluster>/...` in the GitOps repo (with at least the app `values.yaml` files you want to populate).
2. In this repo, add a `clusters.<cluster>:` block listing the apps that should deploy to it.
3. (Optional) Add a `deploy_in_<cluster>` input to `gitops-update.yml` if you want callers to be able to force-off the new cluster individually.

### Force-off semantics

`deploy_in_<cluster>` inputs default to `true` and only **subtract** from the manifest-resolved set:

| Manifest says | Input value | Result |
|---|---|---|
| App included in cluster | `true` (default) | Deploys to cluster |
| App included in cluster | `false` | **Suppressed** — does not deploy |
| App NOT included in cluster | `true` (default) | Does not deploy |
| App NOT included in cluster | `false` | Does not deploy |

Inputs cannot **add** a cluster that the manifest does not list — that prevents accidental cross-cluster spillover.

### Apps not in the manifest

If `app_name` is not found in any cluster, the workflow logs a warning and exits cleanly (no failure). This is the expected behavior for apps managed manually or by other tooling.

## Multi-Server Path Generation

The workflow dynamically generates paths for each server and environment combination:

```
gitops/environments/<server>/helmfile/applications/<env>/<app_name>/values.yaml
```

Where:
- `<server>`: any cluster resolved from the deployment matrix (current set: `firmino`, `clotilde`, `anacleto`), minus those force-off via `deploy_in_<cluster>: false`
- `<env>`: `dev`, `stg`, `prd`, or `sandbox` (determined by tag type)
- `<app_name>`: from `inputs.app_name` or auto-detected from repository name

### Environment-to-Files Mapping

| Tag Type | Environment Label | Environments Updated |
|----------|------------------|----------------------|
| `v*.*.*-beta.*` | beta/dev | `dev` on selected servers |
| `v*.*.*-rc.*` | rc/stg | `stg` on selected servers |
| `v*.*.*` (no suffix) | production | `dev`, `stg`, `prd`, `sandbox` on selected servers |
| `v*.*.*-sandbox.*` | sandbox | `sandbox` on selected servers |

### File Existence Validation

The workflow validates that values files exist before applying tags:

1. **If a file is missing:** A warning is logged and the file is skipped
2. **The workflow never fails due to missing files** - it simply logs and continues

This allows for partial deployments where not all server/environment combinations have values files configured.

### Example: Production Release

When a production tag (e.g., `v1.2.3`) is pushed for an app declared in all three clusters, the workflow will:

1. Resolve cluster set from manifest: `firmino`, `clotilde`, `anacleto`.
2. For each cluster, generate paths for every production environment (`dev`, `stg`, `prd`, `sandbox`):
   - `gitops/environments/<cluster>/helmfile/applications/<env>/my-app/values.yaml`
3. Apply tags to all existing files (skip missing ones with warning).
4. Sync ArgoCD apps for each cluster/environment where files were updated.

## ArgoCD Multi-Server Sync

When `enable_argocd_sync` is `true`, the workflow syncs ArgoCD applications for each server/environment where files were successfully updated.

### App Naming Pattern

ArgoCD apps are named using the pattern: `<server>-<app_name>-<env>`

Examples:
- `firmino-midaz-dev`, `firmino-midaz-stg`, `firmino-midaz-prd`
- `clotilde-midaz-dev`, `clotilde-midaz-stg`, `clotilde-midaz-sandbox`
- `anacleto-midaz-dev`

### Sync Behavior

**Important:** ArgoCD sync only runs for server/environment combinations where values files were actually updated.

| Tag Type | Potential Apps (if files exist) |
|----------|--------------------------------|
| beta | `{server}-{app}-dev` |
| rc | `{server}-{app}-stg` |
| production | `{server}-{app}-dev`, `{server}-{app}-stg`, `{server}-{app}-prd`, `{server}-{app}-sandbox` |
| sandbox | `{server}-{app}-sandbox` |

If a values file doesn't exist for a server/environment, that combination is skipped and ArgoCD sync is NOT triggered for it.

### Matrix-Based Sync

The workflow uses a matrix strategy for ArgoCD sync:
1. The `apply_tags` step outputs a JSON array of server/env combinations that were updated
2. A separate `argocd_sync` job runs in parallel for each combination
3. Each job first checks if the ArgoCD app exists before attempting sync
4. Each sync has `continue-on-error: true` for graceful failure handling

### App Existence Check

Before syncing, each matrix job checks if the ArgoCD app exists:
- **App exists**: Proceeds with sync
- **App doesn't exist**: Logs a warning and skips sync (no failure)

This prevents unnecessary errors when an app hasn't been created in ArgoCD yet for a specific server/environment.

### Graceful Failure

- If one sync fails, other syncs will still attempt
- The overall workflow will continue even if some syncs fail
- Missing apps are logged as warnings, not failures
- Check workflow logs to identify which syncs failed or were skipped

## Migration Guide

### From Single Server to Multi-Server

**Before (single server):**
```yaml
update_gitops:
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@v1.0.0
  with:
    gitops_server: 'firmino'
    gitops_file_dev: gitops/environments/firmino/helmfile/applications/dev/my-app/values.yaml
    gitops_file_stg: gitops/environments/firmino/helmfile/applications/stg/my-app/values.yaml
    gitops_file_prd: gitops/environments/firmino/helmfile/applications/prd/my-app/values.yaml
    yaml_key_mappings: '{"backend.tag": ".auth.image.tag"}'
  secrets: inherit
```

**After (multi-server):**
```yaml
update_gitops:
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@v1.0.0
  with:
    app_name: 'my-app'
    deploy_in_firmino: true
    deploy_in_clotilde: true
    yaml_key_mappings: '{"backend.tag": ".auth.image.tag"}'
  secrets: inherit
```

### Key Changes

1. **Removed inputs:**
   - `gitops_server` - No longer needed; cluster topology is declared in the deployment matrix
   - `gitops_file_dev`, `gitops_file_stg`, `gitops_file_prd`, `gitops_file_sandbox` - Paths are now auto-generated
   - `argocd_app_name` - Now auto-generated based on server/app/env pattern
   - `environment_detection`, `manual_environment` - Simplified to automatic detection only

2. **Inputs that became force-off overrides:**
   - `deploy_in_firmino`, `deploy_in_clotilde`, `deploy_in_anacleto` (all default `true`) — only **subtract** clusters from the manifest-resolved set; cannot add a cluster the manifest does not list

3. **New inputs:**
   - `deployment_matrix_file` (default: `config/deployment-matrix.yml`) — alternative manifest path for forks/testing

4. **Path generation:**
   - Paths are automatically generated based on cluster (from manifest) and environment (from tag)
   - Pattern: `gitops/environments/<cluster>/helmfile/applications/<env>/<app_name>/values.yaml`

5. **ArgoCD sync:**
   - Syncs apps for each cluster/environment combination where files were updated
   - Pattern: `<cluster>-<app_name>-<env>`
   - Checks if app exists before attempting sync

### Migrating an existing caller to manifest-driven topology

> ⚠️ **Semantic change to `deploy_in_*` inputs** — callers that previously relied on `deploy_in_firmino: true` (etc.) to **include** a cluster will now silently deploy nowhere if their app is not listed in the manifest. The inputs only **subtract** from the manifest-resolved set; they never add. The prerequisite for any deployment is a manifest entry. Workflow logs a warning when `app_name` is missing from every cluster, so these cases surface quickly — but add your app to the manifest before merging this bump if you haven't already.

If your caller currently passes `deploy_in_firmino: true, deploy_in_clotilde: true` explicitly:

1. Add your `app_name` to `apps.registry` and to the appropriate `clusters.<name>.apps` lists in [`config/deployment-matrix.yml`](../config/deployment-matrix.yml) (single PR in this repo).
2. Once merged and the caller bumps to the new shared-workflows ref (Renovate/Dependabot), the explicit `deploy_in_*: true` inputs become redundant and can be removed from the caller.
3. Keep `deploy_in_<cluster>: false` only where you want to force-off a cluster the manifest declares.

## Troubleshooting

### No changes to commit

This is normal if the tag already exists in the GitOps repository. The workflow will skip the commit step.

### Values file not found warnings

If you see warnings like "Values file not found for firmino/dev", this means the values.yaml file doesn't exist for that server/environment combination. The workflow will skip this combination and continue with others.

### ArgoCD app does not exist

If you see warnings like "ArgoCD app firmino-myapp-dev does not exist, sync skipped", this means the ArgoCD application hasn't been created yet. The workflow will log a warning and continue.

### Artifact not found

Ensure the artifact pattern matches your uploaded artifacts:
- Pattern: `gitops-tags-*` matches `gitops-tags-backend`, `gitops-tags-frontend`, etc.
- Check artifact names in the build job

### App is not registered in any cluster of the deployment matrix

The workflow logs this warning and exits cleanly when `app_name` is missing from the manifest. Either:
- Add the app to `config/deployment-matrix.yml` in this repo (and bump the caller's pinned ref), or
- Confirm the app is intentionally managed outside this workflow (manual edits, kustomize, separate tooling).

### All clusters resolved from the manifest were suppressed

You explicitly set every `deploy_in_<cluster>: false`. Either remove one of the overrides, or confirm this run is intentionally a no-op.

### YAML key not updated

Verify the YAML key path in your mappings:
- Use `.auth.image.tag` for nested keys
- Use `.image.tag` for root-level keys
- Test with `yq` locally: `yq '.auth.image.tag' values.yaml`

## Best Practices

1. **Add new apps/clusters via the deployment matrix**, not via per-caller `deploy_in_*` flags — single source of truth wins
2. **Reserve `deploy_in_<cluster>: false`** for emergency containment or temporary suppression, not for permanent topology decisions
3. **Use specific artifact patterns** to avoid conflicts
4. **Test with beta tags first** before deploying to production
5. **Monitor ArgoCD sync results** in workflow logs
6. **Keep YAML key mappings simple** and consistent across environments
7. **Pin via Renovate/Dependabot** so manifest updates propagate automatically as new ref bumps
