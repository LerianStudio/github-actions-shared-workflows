# GitOps Update Workflow

Reusable workflow for updating GitOps repository with new image tags across multiple environments.

## Features

- **Convention-based configuration**: Auto-generates paths, names, and patterns from repository name
- **Multi-environment support**: dev (beta), stg (rc), prd (production), sandbox
- **Production + Sandbox sync**: Production releases automatically update both environments
- **Flexible tag mapping**: Static or dynamic YAML key mapping
- **Automatic environment detection**: Based on git tag suffix
- **ArgoCD integration**: Automatic sync after GitOps update (enabled by default)
- **Docker Hub login**: Enabled by default to avoid rate limits
- **Customizable runners**: Support for different GitHub runner types

## Usage

### Minimal Example (Convention-Based)

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
- GitOps paths: `gitops/environments/firmino/helmfile/applications/{env}/my-backend-service/values.yaml`
- ArgoCD app: `firmino-my-backend-service`
- Commit prefix: `my-backend-service`

### Multi-Component Example (Backend + Frontend)

```yaml
update_gitops:
  needs: [build_backend, build_frontend]
  if: needs.build_backend.result == 'success' || needs.build_frontend.result == 'success'
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@main
  with:
    yaml_key_mappings: '{"backend.tag": ".crm.image.tag", "frontend.tag": ".frontend.image.tag"}'
  secrets: inherit
```

### Dynamic Mapping Example (Multiple Components like Midaz)

```yaml
update_gitops:
  needs: build_and_publish
  if: contains(github.ref, '-beta') || contains(github.ref, '-rc')
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@main
  with:
    use_dynamic_mapping: true
    yaml_key_mappings: '{"prefix": "midaz-"}'
  secrets: inherit
```

### Manual Environment Selection

```yaml
update_gitops:
  needs: build_backend
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@main
  with:
    environment_detection: 'manual'
    manual_environment: 'sandbox'
    gitops_file_sandbox: gitops/environments/firmino/helmfile/applications/sandbox/my-backend-service/values.yaml
    artifact_pattern: 'gitops-tags-backend'
    yaml_key_mappings: |
      {
        "backend.tag": ".auth.image.tag"
      }
    commit_message_prefix: 'my-backend-service'
    enable_argocd_sync: false
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
| `gitops_repository` | string | `MyOrg/my-gitops-repo` | GitOps repository to update |
| `gitops_server` | string | `firmino` | Server name for GitOps path generation |
| `app_name` | string | (repo name) | Application name (auto-detected from repository) |
| `artifact_pattern` | string | `gitops-tags-{app}-*` | Pattern to download artifacts (auto-generated) |
| `commit_message_prefix` | string | (repo name) | Prefix for commit message (auto-generated) |
| `argocd_app_name` | string | `{server}-{app}` | ArgoCD application name (auto-generated) |
| `gitops_file_dev` | string | (auto-generated) | Path to dev environment values.yaml |
| `gitops_file_stg` | string | (auto-generated) | Path to stg environment values.yaml |
| `gitops_file_prd` | string | (auto-generated) | Path to prd environment values.yaml |
| `gitops_file_sandbox` | string | (auto-generated) | Path to sandbox environment values.yaml |
| `runner_type` | string | `firmino-lxc-runners` | GitHub runner type |
| `enable_argocd_sync` | boolean | `true` | Enable ArgoCD sync |
| `use_dynamic_mapping` | boolean | `false` | Use dynamic mapping for multiple components |
| `yq_version` | string | `v4.44.3` | Version of yq to install |
| `environment_detection` | string | `tag_suffix` | Environment detection strategy (`tag_suffix` or `manual`) |
| `manual_environment` | string | - | Manually specify environment (dev/stg/prd/sandbox) |
| `enable_docker_login` | boolean | `true` | Enable Docker Hub login to avoid rate limits |

## Secrets

### Required Secrets

| Secret | Description |
|--------|-------------|
| `manage_token` | GitHub token with access to GitOps repository |
| `ci_cd_user_name` | Git user name for commits |
| `ci_cd_user_email` | Git user email for commits |

### Required Secrets (ArgoCD)

| Secret | Description |
|--------|-------------|
| `argocd_token` | ArgoCD authentication token |
| `argocd_url` | ArgoCD server URL |

### Required Secrets (Docker Hub)

| Secret | Description |
|--------|-------------|
| `docker_username` | Docker Hub username (to avoid rate limits) |
| `docker_password` | Docker Hub password |

## Convention-Based Configuration

The workflow automatically generates configuration based on repository name:

**For repository `my-api-service`:**
- **App name**: `my-api-service`
- **Artifact pattern**: `gitops-tags-my-api-service-*`
- **Commit prefix**: `my-api-service`
- **ArgoCD app**: `firmino-my-api-service`
- **GitOps paths**:
  - Dev: `gitops/environments/firmino/helmfile/applications/dev/my-api-service/values.yaml`
  - Stg: `gitops/environments/firmino/helmfile/applications/stg/my-api-service/values.yaml`
  - Prd: `gitops/environments/firmino/helmfile/applications/prd/my-api-service/values.yaml`
  - Sandbox: `gitops/environments/firmino/helmfile/applications/sandbox/my-api-service/values.yaml`

## Environment Detection

The workflow automatically detects the target environment based on git tag suffix:

| Tag Pattern | Environment | Files Updated | ArgoCD Synced |
|-------------|-------------|---------------|---------------|
| `v*.*.*-beta.*` | dev | dev only | dev |
| `v*.*.*-rc.*` | stg | stg only | stg |
| `v*.*.*` (no suffix) | prd | **prd + sandbox** | **prd + sandbox** |

**Note**: Production releases automatically update both production and sandbox environments.

## YAML Key Mappings

### Static Mapping

Used for simple, predefined key mappings:

```json
{
  "backend.tag": ".auth.image.tag",
  "frontend.tag": ".frontend.image.tag"
}
```

The workflow will:
1. Find artifacts matching the key pattern (e.g., files containing "backend.tag")
2. Read the tag value from the artifact
3. Update the specified YAML key (e.g., `.auth.image.tag`)

### Dynamic Mapping

Used for multiple components with consistent naming:

```json
{
  "prefix": "myapp-"
}
```

The workflow expects artifact files named: `{app-name}={version}`

Example: `myapp-auth=1.2.3-rc.1`

The workflow will:
1. Parse the artifact filename
2. Remove the prefix (e.g., "myapp-" → "auth")
3. Update `.{component}.image.tag` (e.g., `.auth.image.tag`)

## Artifact Requirements

### For Static Mapping

Artifacts should contain the tag value and match the key pattern:

```bash
# Example: Create artifact for backend
mkdir -p gitops-tags
echo "1.2.3-beta.1" > gitops-tags/backend.tag

# Upload artifact
- uses: actions/upload-artifact@v4
  with:
    name: gitops-tags-backend
    path: gitops-tags/
```

### For Dynamic Mapping

Artifacts should be named: `{app-name}={version}`

```bash
# Example: Create artifact for myapp-auth
mkdir -p gitops-tags
echo "myapp-auth=1.2.3-rc.1" > "gitops-tags/myapp-auth=1.2.3-rc.1"

# Upload artifact
- uses: actions/upload-artifact@v4
  with:
    name: gitops-tags-myapp-auth
    path: gitops-tags/
```

## Migration Guide

### From Single Component App

**Before:**
```yaml
update_gitops_backend:
  needs: build_backend
  if: ${{ needs.build_backend.result == 'success' }}
  runs-on: firmino-lxc-runners
  steps:
    # ... 80+ lines of code ...
```

**After:**
```yaml
update_gitops_backend:
  needs: build_backend
  if: ${{ needs.build_backend.result == 'success' }}
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@main
  with:
    gitops_file_dev: gitops/environments/firmino/helmfile/applications/dev/my-backend-service/values.yaml
    gitops_file_stg: gitops/environments/firmino/helmfile/applications/stg/my-backend-service/values.yaml
    artifact_pattern: 'gitops-tags-backend'
    yaml_key_mappings: '{"backend.tag": ".auth.image.tag"}'
    commit_message_prefix: 'my-backend-service'
    argocd_app_name: 'firmino-my-backend-service'
  secrets: inherit
```

### From Multi-Component App

**Before:**
```yaml
update_gitops:
  needs: [detect_changes, build_backend, build_frontend]
  # ... complex conditions ...
  runs-on: ubuntu-latest
  steps:
    # ... 90+ lines of code ...
```

**After:**
```yaml
update_gitops:
  needs: [detect_changes, build_backend, build_frontend]
  if: |
    (needs.detect_changes.outputs.has_backend == 'true' && needs.build_backend.result == 'success') ||
    (needs.detect_changes.outputs.has_frontend == 'true' && needs.build_frontend.result == 'success')
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@main
  with:
    gitops_file_dev: gitops/environments/firmino/helmfile/applications/dev/my-fullstack-app/values.yaml
    gitops_file_stg: gitops/environments/firmino/helmfile/applications/stg/my-fullstack-app/values.yaml
    artifact_pattern: 'gitops-tags-my-fullstack-app-*'
    yaml_key_mappings: |
      {
        "backend.tag": ".api.image.tag",
        "frontend.tag": ".web.image.tag"
      }
    commit_message_prefix: 'my-fullstack-app'
    argocd_app_name: 'firmino-my-fullstack-app'
    runner_type: 'ubuntu-latest'
  secrets: inherit
```

### From Monorepo with Dynamic Mapping

**Before:**
```yaml
update_gitops:
  needs: [build_and_publish]
  if: ${{ contains(github.ref, '-beta') || contains(github.ref, '-rc') }}
  runs-on: firmino-lxc-runners
  steps:
    # ... 60+ lines of code with complex logic ...
```

**After:**
```yaml
update_gitops:
  needs: [build_and_publish]
  if: ${{ contains(github.ref, '-beta') || contains(github.ref, '-rc') }}
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@main
  with:
    gitops_file_dev: gitops/environments/firmino/helmfile/applications/dev/my-platform/values.yaml
    gitops_file_stg: gitops/environments/firmino/helmfile/applications/stg/my-platform/values.yaml
    artifact_pattern: 'gitops-tags-*'
    use_dynamic_mapping: true
    yaml_key_mappings: '{"prefix": "myapp-"}'
    commit_message_prefix: 'my-platform'
    argocd_app_name: 'firmino-my-platform'
  secrets: inherit
```

## Troubleshooting

### No changes to commit

This is normal if the tag already exists in the GitOps repository. The workflow will skip the commit step.

### Environment detection failed

Ensure your git tags follow the expected pattern:
- Beta: `v1.2.3-beta.1`
- RC: `v1.2.3-rc.1`
- Production: `v1.2.3`
- Sandbox: `v1.2.3-sandbox.1`

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

1. **Use specific artifact patterns** to avoid conflicts
2. **Enable checksum verification** for production environments
3. **Test with sandbox environment** before deploying to production
4. **Use dynamic mapping** for applications with multiple components
5. **Keep YAML key mappings simple** and consistent across environments
6. **Always specify all environment files** (dev, stg, prd) for flexibility
