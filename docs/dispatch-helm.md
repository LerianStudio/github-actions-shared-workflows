<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>dispatch-helm</h1></td>
  </tr>
</table>

Reusable workflow that sends a **single** `workflow_dispatch` to a Helm chart repository carrying every component of a release, so the chart is updated in one commit instead of one per component.

It also classifies the release: when the tag being dispatched was cut from a maintenance branch, the payload is flagged as a **legacy patch** so the Helm side updates the matching legacy chart line instead of overwriting the mainline chart. See [helm-update-chart](helm-update-chart.md) for the receiving end.

## Inputs

| Input | Description | Required | Default |
|---|---|---|---|
| `helm_repository` | Helm repository to dispatch to (`org/repo`) | yes | — |
| `chart` | Helm chart name (must match the chart directory) | yes | — |
| `version` | Version applied to all components. A leading `v` is stripped. | yes | — |
| `target_ref` | Ref of the Helm repository the dispatched workflow runs on | no | `main` |
| `workflow_file` | Workflow file to trigger in the Helm repository | no | `app-sync.yml` |
| `paths_matrix` | Raw paths matrix from the changed-paths action. Use with `path_mapping`. | no | — |
| `path_mapping` | JSON mapping of paths to app names | no | — |
| `components_json` | JSON array of components — alternative to `paths_matrix` | no | — |
| `components_base_path` | Base path for components in the source repository | no | `components` |
| `env_file` | Env example file relative to the component path | no | `.env.example` |
| `detect_env_changes` | Detect environment variables added since the previous release | no | `true` |
| `values_key_mappings` | JSON mapping of component names to `values.yaml` keys | no | `''` |
| `legacy_patch_detection` | Flag releases cut from maintenance branches as legacy patches | no | `true` |
| `legacy_branch_patterns` | Glob patterns (newline or comma separated) of maintenance branches | no | `maintenance/*` |
| `runner_type` | GitHub runner type | no | `blacksmith-4vcpu-ubuntu-2404` |

## Secrets

| Secret | Description | Required |
|---|---|---|
| `helm_repo_token` | Token scoped to the Helm repository with `Actions: read and write`. That is the only permission the dispatch needs — a classic token with full `repo` scope also works but grants far more than required. | yes |

## Payload

```json
{
  "chart": "my-app",
  "components": [
    { "name": "my-app-api", "values_key": "api", "version": "1.4.2", "env_vars": {} }
  ],
  "has_new_env_vars": false,
  "source_repo": "org/my-app",
  "source_sha": "0d1f2a3…",
  "source_ref": "v1.4.2",
  "source_actor": "someone",
  "source_branch": "maintenance/v1.4.x",
  "is_legacy_patch": true,
  "version_line": "1.4"
}
```

`source_branch`, `is_legacy_patch` and `version_line` are additive — receivers that ignore them behave exactly as before.

## Legacy patch detection

The workflow runs on a tag push, so `github.ref` is the tag and the originating branch is not available from the event. Detection is topological instead:

1. The checkout uses `fetch-depth: 0`, so every remote branch is present.
2. `git for-each-ref --contains HEAD refs/remotes/origin/` lists the branches that contain the tagged commit.
3. Each branch is matched against `legacy_branch_patterns`. The first match wins, and additional matches are reported as warnings.
4. `version_line` is the `X.Y` prefix of `version` — `v1.4.2` becomes `1.4`.

When nothing matches, `is_legacy_patch` is `false` and the payload is functionally identical to the pre-feature one.

### Opting out

Detection is on by default at every layer, because the alternative — a maintenance release rewriting the mainline chart — is the bug this exists to prevent. Each orchestrator that reaches this workflow exposes equivalent detection settings, but the input names are layer-specific. Use the names listed for your entry point:

| Caller uses | Inputs |
|---|---|
| `go-release.yml` | `helm_legacy_patch_detection`, `helm_legacy_branch_patterns` |
| `build.yml` | `helm_legacy_patch_detection`, `helm_legacy_branch_patterns` |
| `js-release.yml` → `typescript-build.yml` | `helm_legacy_patch_detection`, `helm_legacy_branch_patterns` |
| `dispatch-helm.yml` directly | `legacy_patch_detection`, `legacy_branch_patterns` |

In `go-release.yml`, an `extra_builds` group may override both per group. An explicit value on the group — `true` or `false` — wins over the top-level input; omitting the key inherits it.

The chart repository has an independent switch: `legacy_patch_enabled` on [helm-update-chart](helm-update-chart.md) makes it ignore the flag and send every payload to `base_branch`.

## Usage

Recommended — path mapping:

```yaml
env:
  PATH_MAPPING: |
    {
      "src": {"name": "my-api", "context": "."},
      "console": {"name": "my-console", "context": "console"}
    }

jobs:
  dispatch-helm:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/dispatch-helm.yml@v1.54.0
    with:
      helm_repository: LerianStudio/helm
      chart: my-app
      target_ref: main
      version: ${{ github.ref_name }}
      paths_matrix: ${{ needs.detect.outputs.matrix }}
      path_mapping: ${{ env.PATH_MAPPING }}
    secrets:
      helm_repo_token: ${{ secrets.HELM_REPO_TOKEN }}
```

Advanced — explicit components:

```yaml
jobs:
  dispatch-helm:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/dispatch-helm.yml@v1.54.0
    with:
      helm_repository: LerianStudio/helm
      chart: my-app
      version: ${{ github.ref_name }}
      components_json: '[{"name":"backend","version":"1.0.0"},{"name":"frontend","version":"1.0.0"}]'
    secrets:
      helm_repo_token: ${{ secrets.HELM_REPO_TOKEN }}
```

Most callers reach this workflow through [`build.yml`](../.github/workflows/build.yml) rather than directly:

```yaml
jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/build.yml@v1.54.0
    with:
      enable_helm_dispatch: true
      helm_chart: my-app
      helm_values_key_mappings: '{"my-app-api": "api"}'
      # defaults shown for reference
      helm_legacy_patch_detection: true
      helm_legacy_branch_patterns: 'maintenance/*'
    secrets: inherit
```

Testing against a branch:

```yaml
uses: LerianStudio/github-actions-shared-workflows/.github/workflows/dispatch-helm.yml@develop
```

## Required permissions

The dispatch itself is authenticated by `helm_repo_token`, so the calling job needs no elevated permission:

```yaml
permissions:
  contents: read
```
