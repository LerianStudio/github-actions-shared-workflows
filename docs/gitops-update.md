<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>gitops-update</h1></td>
  </tr>
</table>

Reusable workflow for updating GitOps repository with new image tags across multiple clusters and environments.

## Features

- **Manifest-driven topology**: Cluster membership per app is declared in [`config/deployment-matrix.yml`](../config/deployment-matrix.yml) — no caller-side configuration required to add a cluster to an existing app
- **Multi-cluster deployment**: Deploy to Anacleto and Benedita with dynamic path generation
- **Per-cluster env variants**: `env_suffixes` and `env_contexts` support multi-tenant (`-st`/`-mt`) and context-based (`chaos/`, `fuzzing/`) layouts
- **Per-app env exceptions**: `app_extra_envs` adds extra envs for a specific app and release type (e.g. a beta also refreshing `stg-mt`), without changing the defaults for every other app
- **Force-off overrides**: `deploy_in_<cluster>` inputs can suppress a cluster declared in the manifest, useful for emergency containment without editing the manifest
- **Convention-based configuration**: Auto-generates paths, names, and patterns from repository name
- **Multi-environment support**: dev (beta), stg (rc), prd (production), sandbox
- **Configurable per-release environments**: Each release type targets its own environment by default (beta→`dev`, rc→`stg`, stable→`prd`), overridable via `beta_environments` / `rc_environments` / `stable_environments`
- **File existence validation**: Graceful handling of missing values files with warnings (never fails)
- **Flexible tag mapping**: Static or dynamic YAML key mapping
- **Automatic environment detection**: Based on git tag suffix
- **ArgoCD integration**: Automatic sync for each cluster/environment combination where files were updated
- **App existence check**: Verifies ArgoCD app exists before attempting sync
- **Org-level configuration**: Runner, gitops repo, and ArgoCD URL resolved from org variables (`GITOPS_RUNNERS`, `GITOPS_REPOSITORY`, `ARGOCD_URL`)

## Usage

### Minimal Example (Manifest-Driven)

```yaml
update_gitops:
  needs: build_backend
  if: needs.build_backend.result == 'success'
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@tier-1
  with:
    yaml_key_mappings: '{"backend.tag": ".auth.image.tag"}'
  secrets: inherit
```

> **Required Secrets**: `MANAGE_TOKEN`, `LERIAN_CI_CD_USER_NAME`, `LERIAN_CI_CD_USER_EMAIL`, `ARGOCD_TOKEN`, `DOCKER_USERNAME`, `DOCKER_PASSWORD`
>
> **Required Variables**: `GITOPS_REPOSITORY`, `GITOPS_RUNNERS`, `ARGOCD_URL`

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
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@tier-1
  with:
    deploy_in_anacleto: false
    yaml_key_mappings: '{"backend.tag": ".auth.image.tag"}'
  secrets: inherit
```

`deploy_in_<cluster>` inputs only **subtract** clusters from the resolved set — they cannot add a cluster the manifest does not list.

### Kustomize Example (Single-Cluster, No Env Split)

For apps managed via kustomize manifests (no helm chart, no env split), set `gitops_layout: kustomize` and provide the path + image reference. The workflow runs `kustomize edit set image` instead of patching `values.yaml`.

```yaml
update_gitops:
  needs: build
  if: needs.build.result == 'success'
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@tier-1
  with:
    gitops_repository: LerianStudio/midaz-firmino-gitops
    gitops_layout: kustomize
    kustomize_base_path: environments/anacleto/kustomize/ungoliant-controller
    kustomize_image_name: ghcr.io/lerianstudio/ungoliant-controller
    argocd_app_name_template: '{server}-{app}'
  secrets: inherit
```

Notes:
- `yaml_key_mappings` is **not required** for kustomize layouts.
- When `kustomize_base_path` does not contain `${ENV}` and `kustomize_environments` is empty, the workflow runs once per resolved cluster (no env loop).
- Use `${SERVER}` / `${ENV}` placeholders in `kustomize_base_path` for multi-cluster / multi-env kustomize layouts (e.g. `environments/${SERVER}/kustomize/${ENV}/my-app`).
- `configmap_updates` is ignored under `gitops_layout=kustomize` (out of scope for v1).

### Kustomize with More Than One Image

When a single release publishes several images into the same `kustomization.yaml` — for example a controller and a slimmer read API built from the same module — map each extra image to the artifact that carries its tag. Every downloaded artifact file is named after the app that built it (`build.yml` writes `gitops-tags/<app>.tag`), and that name is the mapping key.

```yaml
update_gitops:
  needs: build
  if: needs.build.result == 'success'
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@tier-1
  with:
    gitops_repository: LerianStudio/midaz-firmino-gitops
    gitops_layout: kustomize
    kustomize_base_path: environments/anacleto/kustomize/ungoliant-controller
    kustomize_image_name: ghcr.io/lerianstudio/ungoliant-controller
    kustomize_image_mappings: |
      {
        "ungoliant-api": "ghcr.io/lerianstudio/ungoliant-api"
      }
    artifact_pattern: 'gitops-tags-*'
    argocd_app_name_template: '{server}-{app}'
  secrets: inherit
```

Notes:
- Artifacts absent from the mapping fall back to `kustomize_image_name`, so single-image callers need no mapping at all.
- An artifact that resolves to neither (empty mapping entry and empty `kustomize_image_name`) is skipped with a warning instead of being written under the wrong image name.
- `artifact_pattern` must match the extra apps too. The default derived from the repository name only matches the primary app, so a second image named after a component needs a broader pattern such as `gitops-tags-*`.
- All images resolve into the same `kustomization.yaml` (`kustomize_base_path`). A second image living under a different path is not supported yet.

### Multi-Component Example (Midaz)

```yaml
update_gitops:
  needs: build
  if: needs.build.result == 'success'
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@tier-1
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
| `yaml_key_mappings` | JSON object mapping artifact names to YAML keys. Required when `gitops_layout=helmfile` (default); ignored when `gitops_layout=kustomize` | `{"backend.tag": ".auth.image.tag"}` |

### Optional Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `gitops_repository` | string | `LerianStudio/midaz-firmino-gitops` | GitOps repository to update |
| `app_name` | string | (repo name) | Application name (auto-detected from repository) |
| `deploy_in_anacleto` | boolean | `true` | Force-off override for Anacleto (`false` = subtract from manifest-resolved set) |
| `deployment_matrix_file` | string | `config/deployment-matrix.yml` | Path to the deployment matrix manifest within the shared-workflows checkout |
| `deployment_matrix_ref` | string | `main` | Git ref of `LerianStudio/github-actions-shared-workflows` to read the deployment matrix from. Default `main` ensures all callers see manifest updates immediately, regardless of the workflow ref they pin. Override only when testing a branch. |
| `artifact_pattern` | string | `gitops-tags-{app}-*` | Pattern to download artifacts (auto-generated) |
| `commit_message_prefix` | string | (repo name) | Prefix for commit message (auto-generated) |
| `runner_type` | string | `blacksmith-4vcpu-ubuntu-2404` | GitHub runner type |
| `enable_argocd_sync` | boolean | `true` | Enable ArgoCD sync |
| `argocd_prune` | boolean | `false` | Pass `--prune` to `argocd app sync` so orphaned resources are cleaned up automatically. Opt-in; safer left disabled in production |
| `use_dynamic_mapping` | boolean | `false` | Use dynamic mapping for multiple components |
| `yq_version` | string | `v4.44.3` | Version of yq to install |
| `enable_docker_login` | boolean | `true` | Enable Docker Hub login to avoid rate limits |
| `configmap_updates` | string | - | JSON object mapping artifact names to configmap keys. Helmfile layout only; ignored for kustomize |
| `gitops_layout` | string | `helmfile` | GitOps layout strategy: `helmfile` (default) or `kustomize` |
| `kustomize_base_path` | string | - | Required when `gitops_layout=kustomize`. Path within the gitops repo to the kustomization folder. Supports `${SERVER}` / `${ENV}` placeholders |
| `kustomize_image_name` | string | - | Required when `gitops_layout=kustomize`, unless every image is covered by `kustomize_image_mappings`. Image reference matched by `kustomize edit set image`; also the fallback for artifacts absent from the mapping |
| `kustomize_image_mappings` | string | - | JSON object mapping artifact names to kustomize image references. Use when one release publishes more than one image into the same `kustomization.yaml`. Kustomize layout only |
| `kustomize_environments` | string | - | Optional space-separated env list overriding the default tag-based env loop when `gitops_layout=kustomize`. Leave empty for layouts without env split |
| `kustomize_version` | string | `v5.4.3` | Version of kustomize CLI to install (only when `gitops_layout=kustomize`) |
| `argocd_app_name_template` | string | `{server}-{app}-{env}` | Template for the ArgoCD application name. Supports `{server}`, `{app}`, `{env}`. For kustomize layouts without env split, use e.g. `{server}-{app}` |
| `argocd_sync_timeout` | number | `600` | Timeout in seconds for `argocd app wait` after sync. Increase for larger applications or clusters under load. |
| `beta_environments` | string | `dev` | Space-separated environments updated by a beta release (`develop` branch) |
| `rc_environments` | string | `stg` | Space-separated environments updated by an rc release (`release-candidate` branch) |
| `stable_environments` | string | `prd` | Space-separated environments updated by a stable release (`main` branch). Default `prd` so a hotfix does not overwrite features still in dev/stg. Set to `dev stg prd` to refresh lower environments too. Sandbox is controlled separately by `update_sandbox` |

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
| `ARGOCD_TOKEN` | ArgoCD authentication token |

### Required Variables

| Variable | Description |
|----------|-------------|
| `GITOPS_REPOSITORY` | GitOps repository to update (e.g. `LerianStudio/lerian-internal-gitops`) |
| `GITOPS_RUNNERS` | GitHub Actions runner label for the gitops/deploy jobs (e.g. `eveo-lxc-runners`) |
| `ARGOCD_URL` | ArgoCD server hostname without protocol (e.g. `argocd.eveo.lerian.net`) |

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

### Per-cluster env context directories (Anacleto)

Some clusters organize their helmfile tree with an extra **context** level before the env. Anacleto uses this to separate chaos and fuzzing test suites:

```
environments/anacleto/helmfile/applications/
├── chaos/
│   ├── dev-st/{app}/values.yaml
│   └── dev-mt/{app}/values.yaml
└── fuzzing/
    ├── dev-st/{app}/values.yaml
    └── dev-mt/{app}/values.yaml
```

Declare the contexts on the cluster block alongside `env_suffixes`:

```yaml
clusters:
  anacleto:
    env_contexts: ["chaos", "fuzzing"]   # path prefix before the env
    env_suffixes: ["-st", "-mt"]         # variant suffix appended to the env
    apps: [midaz, fetcher, ...]
```

| Field | Default | Effect |
|---|---|---|
| `env_contexts` | `[]` | List of subdirectory prefixes inserted before the env in the helmfile path. When empty, no prefix is added (existing behavior). |
| `env_suffixes` | `[""]` | List of suffixes appended to each tag-derived env. |

**Resolution on a beta tag** (env: `dev`), with the manifest above:

1. Tag-type → base env: `dev`
2. Suffix expansion: `dev` → `dev-st`, `dev-mt`
3. Context expansion: for each context × each variant:
   - `chaos` × `dev-st` → `chaos/dev-st`
   - `chaos` × `dev-mt` → `chaos/dev-mt`
   - `fuzzing` × `dev-st` → `fuzzing/dev-st`
   - `fuzzing` × `dev-mt` → `fuzzing/dev-mt`
4. Final env list for anacleto: `chaos/dev-st chaos/dev-mt fuzzing/dev-st fuzzing/dev-mt`
5. Values paths: `environments/anacleto/helmfile/applications/{context/env}/{app}/values.yaml`
6. ArgoCD app name: `/` normalized to `-`, so `{server}-{app}-chaos/dev-st` → `anacleto-midaz-chaos-dev-st`

Clusters without `env_contexts` (benedita) are unaffected — the field defaults to `[]`.

### Per-cluster env suffix variants (`-st`, `-mt`, ...)

Some clusters host **multiple parallel variants per environment** as sibling namespaces, helmfile directories, and ArgoCD apps. For example, Benedita runs both single-tenant (`-st`) and multi-tenant (`-mt`) variants:

```
environments/benedita/helmfile/applications/
├── dev-st/midaz/values.yaml
├── stg-st/midaz/values.yaml
├── stg-mt/midaz/values.yaml       # the only -mt variant that exists
├── prd-st/midaz/values.yaml
└── sandbox/midaz/values.yaml      # shared, no suffix
```

Note the variants are **not** symmetric across environments: on Benedita the `-mt` variant exists only for `stg`. There is no `dev-mt` or `prd-mt` (see the cluster block in [`config/deployment-matrix.yml`](../config/deployment-matrix.yml)). Suffix expansion is mechanical and does not know that, so it still produces `dev-mt` and `prd-mt`; those iterations find no values file and are skipped with a warning, per [File Existence Validation](#file-existence-validation). That asymmetry is what [`app_extra_envs`](#per-app-env-exceptions-app_extra_envs) exists to work around.

Declare the suffixes on the cluster block:

```yaml
clusters:
  benedita:
    env_suffixes: ["-st", "-mt"]         # produces dev-st, dev-mt, stg-st, ...
    suffix_excludes_envs: ["sandbox"]    # sandbox stays bare (no suffix)
    apps: [midaz, fetcher, ...]
```

| Field | Default | Effect |
|---|---|---|
| `env_suffixes` | `[""]` | List of suffixes appended to each tag-derived env. `[""]` (the default) preserves the pre-existing single-variant behavior. |
| `suffix_excludes_envs` | `[]` | Tag-derived env names that stay bare (no suffix expansion). Useful for shared envs like `sandbox`. |

**Resolution on a production tag**, with the manifest above:

1. Tag-type → env list (existing logic): `dev stg prd sandbox`
2. Cluster expansion (new logic): for benedita, expand each env not in `suffix_excludes_envs` against `env_suffixes`:
   - `dev` → `dev-st`, `dev-mt`
   - `stg` → `stg-st`, `stg-mt`
   - `prd` → `prd-st`, `prd-mt`
   - `sandbox` (excluded) → `sandbox`
3. Final env list for benedita: `dev-st dev-mt stg-st stg-mt prd-st prd-mt sandbox` (7 entries)
4. ArgoCD app name template (default `{server}-{app}-{env}`) resolves to `benedita-midaz-dev-st`, `benedita-midaz-dev-mt`, ..., `benedita-midaz-sandbox`

Firmino, Clotilde, Anacleto behavior is byte-identical to before: with both fields absent, `env_suffixes` defaults to `[""]` (single empty-suffix expansion), so the final env list equals the tag-derived list verbatim.

#### Interaction with `app_helmfile_env`

When an app has an `app_helmfile_env` override (e.g. `forge: cross`), the override path takes precedence and **the suffix expansion is skipped for that app** — it updates once at the override path. The sync target's env is the override value (`cross`), so the ArgoCD app name resolves to `benedita-forge-cross`.

### Per-app env exceptions (`app_extra_envs`)

The suffix expansion above is uniform: every app on the cluster gets the same variants for a given tag type. That breaks down when a variant does not exist in every environment. On Benedita the multi-tenant variant only has `stg-mt` — there is no `dev-mt` — so a **beta release never refreshes the multi-tenant variant of any app**: it targets `dev`, expands to `dev-st` + `dev-mt`, and `dev-mt` is skipped with a *values file not found* warning.

`app_extra_envs` is the per-app exception for exactly this case:

```yaml
clusters:
  benedita:
    env_suffixes: ["-st", "-mt"]
    suffix_excludes_envs: ["sandbox"]
    app_extra_envs:
      midaz:
        beta: ["stg-mt"]        # every beta tag also updates stg-mt
    apps: [midaz, fetcher, ...]
```

| Field | Default | Effect |
|---|---|---|
| `app_extra_envs.<app>.<release_type>` | `{}` | List of **literal** env names unioned into the app's expanded env list for that release type. `release_type` ∈ `beta`, `rc`, `stable`, `sandbox`. |

Rules:

- Values are **literal env names** — they already carry the cluster's suffix and context (`stg-mt`, `chaos/dev-mt`). They are appended verbatim and are **never re-expanded** against `env_suffixes` / `env_contexts`.
- Entries duplicating an env the tag already produced are dropped, so `rc: ["stg-mt"]` on Benedita is a no-op rather than a double update.
- The field is **per cluster**: `stg-mt` under `benedita` has no effect on `anacleto`, whose envs are context-prefixed.
- Mutually exclusive with `app_helmfile_env` for the same app — the helmfile override wins in the env loop and would collapse the extras onto the override path. The deployment-matrix lint rejects the combination.
- Ignored when the caller sets `gitops_layout=kustomize`; those layouts drive the env loop through `kustomize_environments` or the `${ENV}` path placeholder.
- Env names may only contain letters, digits, `.`, `_`, `-` and `/`, and must not be absolute or contain `.`/`..` components. These values become the values-file path and travel through a space-separated env list, so whitespace would silently split one env into two and `..` would point outside `applications/`. `chaos/dev-mt` stays valid.
- The workflow validates `app_extra_envs` up-front and **fails the job** if it is invalid, before any GitOps file is touched. A silent skip would leave the release green while the requested env was never updated — the exact failure this feature prevents. Note an invalid entry is still valid YAML, so cluster resolution does not catch it.

The structure and the env names are checked in **two independent places**, on purpose:

| | Enforced by | Covers |
|---|---|---|
| PR time | `src/lint/deployment-matrix` | Manifests in this repo, every app, with per-field error messages |
| Run time | `gitops-update.yml`, before the env loop | Any manifest, including one read from an unlinted `deployment_matrix_ref` |

The runtime check is not redundant: `deployment_matrix_ref` lets a caller read the matrix from a ref the lint never saw. It fails the job with a single `::error::` rather than pinpointing the field — use the lint for that.

The runtime check has two parts, with deliberately different scopes:

- **Structural**, manifest-wide — types at each level, non-empty leaf lists, and the env-name rules above. A structural break means the manifest is broken, so it fails regardless of which app is releasing.
- **Relational**, scoped to the app being released **and** to the resolved cluster set — the release types must be known, and the app must not also carry an `app_helmfile_env` override on the same cluster. Both would otherwise be silently ignored: an unknown release type such as `beta_typo` never matches, and the helmfile override replaces the tag-derived env for every iteration, so the extra env gets written to the override path instead.

  The double scoping is deliberate. An entry is inert for a given run when it belongs to another app (the lookup is keyed by app name) or to a cluster this run does not target — one that does not host the app, or one suppressed via `deploy_in_<cluster>: false`. Aborting a release over an entry it never consults would be collateral damage, so the check only looks at clusters that survived force-off filtering. The lint still flags those entries at PR time, where nothing is at stake.

**Resolution on a beta tag** for `midaz` on benedita, with the manifest above:

1. Tag-type → base env: `dev`
2. Suffix expansion: `dev-st`, `dev-mt`
3. Extras for `beta`: `stg-mt`
4. Final env list: `dev-st dev-mt stg-mt`
5. Sync targets: `benedita-midaz-dev-st`, `benedita-midaz-dev-mt`, `benedita-midaz-stg-mt`

⚠️ **Operational consequence**: the beta image stays running in `stg-mt` until the next rc release overwrites it. That is the point of the exception, but it means `stg-mt` is no longer an rc-only environment for the listed apps. Keep the list narrow and deliberate.

Apps not listed are unaffected, and a cluster without `app_extra_envs` behaves exactly as before.

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
- `<server>`: any cluster resolved from the deployment matrix (current set: `anacleto`, `benedita`), minus those force-off via `deploy_in_<cluster>: false`
- `<env>`: `dev`, `stg`, `prd`, or `sandbox` (determined by tag type)
- `<app_name>`: from `inputs.app_name` or auto-detected from repository name

### Environment-to-Files Mapping

| Tag Type | Environment Label | Environments Updated (default) |
|----------|------------------|----------------------|
| `v*.*.*-beta.*` | beta/dev | `dev` on selected servers (`beta_environments`) |
| `v*.*.*-rc.*` | rc/stg | `stg` on selected servers (`rc_environments`) |
| `v*.*.*` (no suffix) | production | `prd` on selected servers (`stable_environments`), plus `sandbox` when `update_sandbox=true` |
| `v*.*.*-sandbox.*` | sandbox | `sandbox` on selected servers |

These lists apply to every app. For an exception scoped to a single app — such as a beta that must also refresh `stg-mt` — use [`app_extra_envs`](#per-app-env-exceptions-app_extra_envs) in the deployment matrix instead of widening the input for everyone.

The per-type environment lists are configurable via the `beta_environments`, `rc_environments`, and `stable_environments` inputs. By default each release stays scoped to its own environment, so a stable hotfix merged to `main` updates only `prd` and does not overwrite features still living in dev/stg. To have a stable release also refresh the lower environments (previous behavior), set `stable_environments: "dev stg prd"`.

### File Existence Validation

The workflow validates that values files exist before applying tags:

1. **If a file is missing:** A warning is logged and the file is skipped
2. **The workflow never fails due to missing files** - it simply logs and continues

This allows for partial deployments where not all server/environment combinations have values files configured.

### Example: Production Release

When a production tag (e.g., `v1.2.3`) is pushed for an app declared in all three clusters, the workflow will (with default `stable_environments: prd`):

1. Resolve cluster set from manifest: `firmino`, `clotilde`, `anacleto`.
2. For each cluster, generate paths for the stable environment(s) (`prd` by default, plus `sandbox` when `update_sandbox=true`):
   - `gitops/environments/<cluster>/helmfile/applications/<env>/my-app/values.yaml`
3. Apply tags to all existing files (skip missing ones with warning).
4. Sync ArgoCD apps for each cluster/environment where files were updated.

To keep the previous behavior where a stable release also refreshes `dev` and `stg`, set `stable_environments: "dev stg prd"`.

## ArgoCD Multi-Server Sync

When `enable_argocd_sync` is `true`, the workflow syncs ArgoCD applications for each server/environment where files were successfully updated.

### App Naming Pattern

ArgoCD apps are named using the pattern: `<server>-<app_name>-<env>`

Examples:
- `anacleto-midaz-chaos-dev-st`, `anacleto-midaz-fuzzing-dev-mt`
- `benedita-midaz-dev-st`, `benedita-midaz-stg-mt`, `benedita-midaz-sandbox`

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

### Sync Command Behavior

The `argocd app sync` call uses `--async --timeout 180`, dispatching the sync without blocking on completion. On failure, the sync step makes up to 5 attempts with a 30s interval between attempts.

A subsequent `argocd app wait --timeout` (configurable via `argocd_sync_timeout`, default `600`) confirms the rollout. On failure, the wait step makes up to 3 attempts with exponential backoff (30s, then 60s between attempts).

When `argocd_prune` is `true`, `--prune` is appended so orphaned resources left behind by previous renames/removals are cleaned up automatically. Keep this disabled by default in production and enable per-caller when you knowingly need cleanup.

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
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@tier-1
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
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@tier-1
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
   - `deploy_in_anacleto` (default `true`) — only **subtracts** clusters from the manifest-resolved set; cannot add a cluster the manifest does not list

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

1. Add your `app_name` to `apps.registry` and to the appropriate `clusters.<name>.apps` lists in [`config/deployment-matrix.yml`](../config/deployment-matrix.yml) (single PR in this repo).
2. Once merged and the caller bumps to the new shared-workflows ref (Renovate/Dependabot), any explicit `deploy_in_*: true` inputs become redundant and can be removed from the caller.
3. Keep `deploy_in_anacleto: false` only where you want to force-off that cluster.

## Troubleshooting

### No changes to commit

This is normal if the tag already exists in the GitOps repository. The workflow will skip the commit step.

### Values file not found warnings

If you see warnings like "Values file not found for anacleto/chaos/dev-st", this means the values.yaml file doesn't exist for that server/environment combination. The workflow will skip this combination and continue with others.

### ArgoCD app does not exist

If you see warnings like "ArgoCD app anacleto-myapp-chaos-dev-st does not exist, sync skipped", this means the ArgoCD application hasn't been created yet. The workflow will log a warning and continue.

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
