# GitOps Update Workflow

Reusable workflow for updating GitOps repository with new image tags across multiple servers and environments.

## Features

- **Multi-server deployment**: Deploy to Firmino and/or Clotilde servers with dynamic path generation
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

### Minimal Example (Convention-Based, Both Servers)

```yaml
update_gitops:
  needs: build_backend
  if: needs.build_backend.result == 'success'
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@main
  with:
    yaml_key_mappings: '{"backend.tag": ".auth.image.tag"}'
  secrets: inherit
```

> **Required Secrets**: `MANAGE_TOKEN`, `LERIAN_CI_CD_USER_NAME`, `LERIAN_CI_CD_USER_EMAIL`, `ARGOCD_GHUSER_TOKEN`, `ARGOCD_URL`, `DOCKER_USERNAME`, `DOCKER_PASSWORD`

**Auto-generated values** (for repo `my-backend-service`):
- App name: `my-backend-service`
- Artifact pattern: `gitops-tags-my-backend-service-*`
- GitOps paths: 
  - Firmino: `gitops/environments/firmino/helmfile/applications/{env}/my-backend-service/values.yaml`
  - Clotilde: `gitops/environments/clotilde/helmfile/applications/{env}/my-backend-service/values.yaml`
- ArgoCD apps: `firmino-my-backend-service-{env}`, `clotilde-my-backend-service-{env}`
- Commit prefix: `my-backend-service`

### Single Server Example (Firmino Only)

```yaml
update_gitops:
  needs: build_backend
  if: needs.build_backend.result == 'success'
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@main
  with:
    deploy_in_firmino: true
    deploy_in_clotilde: false
    yaml_key_mappings: '{"backend.tag": ".auth.image.tag"}'
  secrets: inherit
```

### Single Server Example (Clotilde Only)

```yaml
update_gitops:
  needs: build_backend
  if: needs.build_backend.result == 'success'
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@main
  with:
    deploy_in_firmino: false
    deploy_in_clotilde: true
    yaml_key_mappings: '{"backend.tag": ".auth.image.tag"}'
  secrets: inherit
```

### Multi-Component Example (Midaz)

```yaml
update_gitops:
  needs: build
  if: needs.build.result == 'success'
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@main
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
| `deploy_in_firmino` | boolean | `true` | Deploy to Firmino server |
| `deploy_in_clotilde` | boolean | `true` | Deploy to Clotilde server |
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

## Multi-Server Path Generation

The workflow dynamically generates paths for each server and environment combination:

```
gitops/environments/<server>/helmfile/applications/<env>/<app_name>/values.yaml
```

Where:
- `<server>`: `firmino` or `clotilde` (controlled by `deploy_in_firmino` and `deploy_in_clotilde` inputs)
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

When a production tag (e.g., `v1.2.3`) is pushed with both servers enabled, the workflow will:

1. Generate paths for Firmino:
   - `gitops/environments/firmino/helmfile/applications/dev/my-app/values.yaml`
   - `gitops/environments/firmino/helmfile/applications/stg/my-app/values.yaml`
   - `gitops/environments/firmino/helmfile/applications/prd/my-app/values.yaml`
   - `gitops/environments/firmino/helmfile/applications/sandbox/my-app/values.yaml`

2. Generate paths for Clotilde:
   - `gitops/environments/clotilde/helmfile/applications/dev/my-app/values.yaml`
   - `gitops/environments/clotilde/helmfile/applications/stg/my-app/values.yaml`
   - `gitops/environments/clotilde/helmfile/applications/prd/my-app/values.yaml`
   - `gitops/environments/clotilde/helmfile/applications/sandbox/my-app/values.yaml`

3. Apply tags to all existing files (skip missing ones with warning)
4. Sync ArgoCD apps for each server/environment where files were updated

## ArgoCD Multi-Server Sync

When `enable_argocd_sync` is `true`, the workflow syncs ArgoCD applications for each server/environment where files were successfully updated.

### App Naming Pattern

ArgoCD apps are named using the pattern: `<server>-<app_name>-<env>`

Examples:
- `firmino-midaz-dev`
- `firmino-midaz-stg`
- `firmino-midaz-prd`
- `clotilde-midaz-dev`
- `clotilde-midaz-stg`

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
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@main
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
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@main
  with:
    app_name: 'my-app'
    deploy_in_firmino: true
    deploy_in_clotilde: true
    yaml_key_mappings: '{"backend.tag": ".auth.image.tag"}'
  secrets: inherit
```

### Key Changes

1. **Removed inputs:**
   - `gitops_server` - No longer needed; use `deploy_in_firmino` and `deploy_in_clotilde` instead
   - `gitops_file_dev`, `gitops_file_stg`, `gitops_file_prd`, `gitops_file_sandbox` - Paths are now auto-generated
   - `argocd_app_name` - Now auto-generated based on server/app/env pattern
   - `environment_detection`, `manual_environment` - Simplified to automatic detection only

2. **New inputs:**
   - `deploy_in_firmino` (default: `true`) - Enable deployment to Firmino server
   - `deploy_in_clotilde` (default: `true`) - Enable deployment to Clotilde server

3. **Path generation:**
   - Paths are automatically generated based on server and environment
   - Pattern: `gitops/environments/<server>/helmfile/applications/<env>/<app_name>/values.yaml`

4. **ArgoCD sync:**
   - Now syncs apps for each server/environment combination where files were updated
   - Pattern: `<server>-<app_name>-<env>`
   - Checks if app exists before attempting sync

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

### YAML key not updated

Verify the YAML key path in your mappings:
- Use `.auth.image.tag` for nested keys
- Use `.image.tag` for root-level keys
- Test with `yq` locally: `yq '.auth.image.tag' values.yaml`

## Best Practices

1. **Start with both servers enabled** - the workflow gracefully handles missing files
2. **Use specific artifact patterns** to avoid conflicts
3. **Test with beta tags first** before deploying to production
4. **Monitor ArgoCD sync results** in workflow logs
5. **Keep YAML key mappings simple** and consistent across environments
