# GitOps Update Workflow

Reusable workflow for updating GitOps repository with new image tags across multiple environments.

## Features

- **Multi-environment support**: dev (beta), stg (rc), prd (production), sandbox
- **Flexible tag mapping**: Static or dynamic YAML key mapping
- **Automatic environment detection**: Based on git tag suffix
- **ArgoCD integration**: Optional automatic sync after GitOps update
- **Checksum verification**: Optional yq binary verification
- **Customizable runners**: Support for different GitHub runner types

## Usage

### Basic Example (Single Component)

```yaml
update_gitops:
  needs: build_backend
  if: ${{ needs.build_backend.result == 'success' }}
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@main
  with:
    gitops_file_dev: gitops/environments/firmino/helmfile/applications/dev/plugin-auth/values.yaml
    gitops_file_stg: gitops/environments/firmino/helmfile/applications/stg/plugin-auth/values.yaml
    gitops_file_prd: gitops/environments/firmino/helmfile/applications/prd/plugin-auth/values.yaml
    artifact_pattern: 'gitops-tags-backend'
    yaml_key_mappings: |
      {
        "backend.tag": ".auth.image.tag"
      }
    commit_message_prefix: 'plugin-auth'
    argocd_app_name: 'firmino-plugin-access-manager'
    enable_docker_login: true
  secrets:
    manage_token: ${{ secrets.MANAGE_TOKEN }}
    ci_cd_user_name: ${{ secrets.LERIAN_CI_CD_USER_NAME }}
    ci_cd_user_email: ${{ secrets.LERIAN_CI_CD_USER_EMAIL }}
    argocd_token: ${{ secrets.ARGOCD_GHUSER_TOKEN }}
    argocd_url: ${{ secrets.ARGOCD_URL }}
    docker_username: ${{ secrets.DOCKER_USERNAME }}
    docker_password: ${{ secrets.DOCKER_PASSWORD }}
```

### Multi-Component Example (Backend + Frontend)

```yaml
update_gitops:
  needs: [build_backend, build_frontend]
  if: |
    (needs.build_backend.result == 'success') ||
    (needs.build_frontend.result == 'success')
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@main
  with:
    gitops_file_dev: gitops/environments/firmino/helmfile/applications/dev/plugin-crm/values.yaml
    gitops_file_stg: gitops/environments/firmino/helmfile/applications/stg/plugin-crm/values.yaml
    gitops_file_prd: gitops/environments/firmino/helmfile/applications/prd/plugin-crm/values.yaml
    artifact_pattern: 'gitops-tags-plugin-crm-*'
    yaml_key_mappings: |
      {
        "backend.tag": ".crm.image.tag",
        "frontend.tag": ".frontend.image.tag"
      }
    commit_message_prefix: 'plugin-crm'
    argocd_app_name: 'firmino-plugin-crm'
    runner_type: 'ubuntu-latest'
  secrets:
    manage_token: ${{ secrets.MANAGE_TOKEN }}
    ci_cd_user_name: ${{ secrets.LERIAN_CI_CD_USER_NAME }}
    ci_cd_user_email: ${{ secrets.LERIAN_CI_CD_USER_EMAIL }}
    argocd_token: ${{ secrets.ARGOCD_GHUSER_TOKEN }}
    argocd_url: ${{ secrets.ARGOCD_URL }}
```

### Dynamic Mapping Example (Multiple Components like Midaz)

```yaml
update_gitops:
  needs: build_and_publish
  if: ${{ contains(github.ref, '-beta') || contains(github.ref, '-rc') }}
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@main
  with:
    gitops_file_dev: gitops/environments/firmino/helmfile/applications/dev/midaz/values.yaml
    gitops_file_stg: gitops/environments/firmino/helmfile/applications/stg/midaz/values.yaml
    gitops_file_prd: gitops/environments/firmino/helmfile/applications/prd/midaz/values.yaml
    artifact_pattern: 'gitops-tags-*'
    use_dynamic_mapping: true
    yaml_key_mappings: |
      {
        "prefix": "midaz-"
      }
    commit_message_prefix: 'midaz'
    argocd_app_name: 'firmino-midaz'
  secrets:
    manage_token: ${{ secrets.MANAGE_TOKEN }}
    ci_cd_user_name: ${{ secrets.LERIAN_CI_CD_USER_NAME }}
    ci_cd_user_email: ${{ secrets.LERIAN_CI_CD_USER_EMAIL }}
    argocd_token: ${{ secrets.ARGOCD_GHUSER_TOKEN }}
    argocd_url: ${{ secrets.ARGOCD_URL }}
```

### Manual Environment Selection

```yaml
update_gitops:
  needs: build_backend
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@main
  with:
    environment_detection: 'manual'
    manual_environment: 'sandbox'
    gitops_file_sandbox: gitops/environments/firmino/helmfile/applications/sandbox/plugin-auth/values.yaml
    artifact_pattern: 'gitops-tags-backend'
    yaml_key_mappings: |
      {
        "backend.tag": ".auth.image.tag"
      }
    commit_message_prefix: 'plugin-auth'
    enable_argocd_sync: false
  secrets:
    manage_token: ${{ secrets.MANAGE_TOKEN }}
    ci_cd_user_name: ${{ secrets.LERIAN_CI_CD_USER_NAME }}
    ci_cd_user_email: ${{ secrets.LERIAN_CI_CD_USER_EMAIL }}
```

## Inputs

### Required Inputs

| Input | Description | Example |
|-------|-------------|---------|
| `artifact_pattern` | Pattern to download artifacts | `gitops-tags-*` |
| `yaml_key_mappings` | JSON object mapping artifact names to YAML keys | `{"backend.tag": ".auth.image.tag"}` |
| `commit_message_prefix` | Prefix for commit message | `plugin-auth` |

### Optional Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `gitops_repository` | string | `LerianStudio/midaz-firmino-gitops` | GitOps repository to update |
| `gitops_file_dev` | string | - | Path to dev environment values.yaml |
| `gitops_file_stg` | string | - | Path to stg environment values.yaml |
| `gitops_file_prd` | string | - | Path to prd environment values.yaml |
| `gitops_file_sandbox` | string | - | Path to sandbox environment values.yaml |
| `runner_type` | string | `firmino-lxc-runners` | GitHub runner type |
| `enable_argocd_sync` | boolean | `true` | Enable ArgoCD sync |
| `argocd_app_name` | string | - | ArgoCD application name |
| `use_dynamic_mapping` | boolean | `false` | Use dynamic mapping for multiple components |
| `yq_version` | string | `v4.44.3` | Version of yq to install |
| `environment_detection` | string | `tag_suffix` | Environment detection strategy (`tag_suffix` or `manual`) |
| `manual_environment` | string | - | Manually specify environment (dev/stg/prd/sandbox) |
| `enable_docker_login` | boolean | `false` | Enable Docker Hub login to avoid rate limits (429 errors) |

## Secrets

### Required Secrets

| Secret | Description |
|--------|-------------|
| `manage_token` | GitHub token with access to GitOps repository |
| `ci_cd_user_name` | Git user name for commits |
| `ci_cd_user_email` | Git user email for commits |

### Optional Secrets

| Secret | Description | Required When |
|--------|-------------|---------------|
| `argocd_token` | ArgoCD authentication token | `enable_argocd_sync` is `true` |
| `argocd_url` | ArgoCD server URL | `enable_argocd_sync` is `true` |
| `docker_username` | Docker Hub username | `enable_docker_login` is `true` |
| `docker_password` | Docker Hub password | `enable_docker_login` is `true` |

## Environment Detection

The workflow automatically detects the target environment based on git tag suffix:

| Tag Pattern | Environment | GitOps File Used |
|-------------|-------------|------------------|
| `*-beta*` | dev | `gitops_file_dev` |
| `*-rc*` | stg | `gitops_file_stg` |
| `*-sandbox*` | sandbox | `gitops_file_sandbox` |
| `v*.*.*` (no suffix) | prd | `gitops_file_prd` |

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
  "prefix": "midaz-"
}
```

The workflow expects artifact files named: `{app-name}={version}`

Example: `midaz-onboarding=1.2.3-rc.1`

The workflow will:
1. Parse the artifact filename
2. Remove the prefix (e.g., "midaz-" → "onboarding")
3. Update `.{component}.image.tag` (e.g., `.onboarding.image.tag`)

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
# Example: Create artifact for midaz-onboarding
mkdir -p gitops-tags
echo "midaz-onboarding=1.2.3-rc.1" > "gitops-tags/midaz-onboarding=1.2.3-rc.1"

# Upload artifact
- uses: actions/upload-artifact@v4
  with:
    name: gitops-tags-midaz-onboarding
    path: gitops-tags/
```

## Migration Guide

### From plugin-auth

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
    gitops_file_dev: gitops/environments/firmino/helmfile/applications/dev/plugin-access-manager/values.yaml
    gitops_file_stg: gitops/environments/firmino/helmfile/applications/stg/plugin-access-manager/values.yaml
    artifact_pattern: 'gitops-tags-backend'
    yaml_key_mappings: '{"backend.tag": ".auth.image.tag"}'
    commit_message_prefix: 'plugin-auth'
    argocd_app_name: 'firmino-plugin-access-manager'
  secrets:
    manage_token: ${{ secrets.MANAGE_TOKEN }}
    ci_cd_user_name: ${{ secrets.LERIAN_CI_CD_USER_NAME }}
    ci_cd_user_email: ${{ secrets.LERIAN_CI_CD_USER_EMAIL }}
    argocd_token: ${{ secrets.ARGOCD_GHUSER_TOKEN }}
    argocd_url: ${{ secrets.ARGOCD_URL }}
```

### From plugin-crm/plugin-fees

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
    gitops_file_dev: gitops/environments/firmino/helmfile/applications/dev/plugin-crm/values.yaml
    gitops_file_stg: gitops/environments/firmino/helmfile/applications/stg/plugin-crm/values.yaml
    artifact_pattern: 'gitops-tags-plugin-crm-*'
    yaml_key_mappings: |
      {
        "backend.tag": ".crm.image.tag",
        "frontend.tag": ".frontend.image.tag"
      }
    commit_message_prefix: 'plugin-crm'
    argocd_app_name: 'firmino-plugin-crm'
    runner_type: 'ubuntu-latest'
  secrets:
    manage_token: ${{ secrets.MANAGE_TOKEN }}
    ci_cd_user_name: ${{ secrets.LERIAN_CI_CD_USER_NAME }}
    ci_cd_user_email: ${{ secrets.LERIAN_CI_CD_USER_EMAIL }}
    argocd_token: ${{ secrets.ARGOCD_GHUSER_TOKEN }}
    argocd_url: ${{ secrets.ARGOCD_URL }}
```

### From midaz

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
    gitops_file_dev: gitops/environments/firmino/helmfile/applications/dev/midaz/values.yaml
    gitops_file_stg: gitops/environments/firmino/helmfile/applications/stg/midaz/values.yaml
    artifact_pattern: 'gitops-tags-*'
    use_dynamic_mapping: true
    yaml_key_mappings: '{"prefix": "midaz-"}'
    commit_message_prefix: 'midaz'
    argocd_app_name: 'firmino-midaz'
  secrets:
    manage_token: ${{ secrets.MANAGE_TOKEN }}
    ci_cd_user_name: ${{ secrets.LERIAN_CI_CD_USER_NAME }}
    ci_cd_user_email: ${{ secrets.LERIAN_CI_CD_USER_EMAIL }}
    argocd_token: ${{ secrets.ARGOCD_GHUSER_TOKEN }}
    argocd_url: ${{ secrets.ARGOCD_URL }}
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
