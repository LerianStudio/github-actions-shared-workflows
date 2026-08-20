<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>lifecycle-management-publish</h1></td>
  </tr>
</table>

Composite action that registers a Helm chart release with Lerian's Plugin Lifecycle Management platform (Distr):

1. Resolves the chart's Application ID from the `application-ids` mapping (`chart:id,chart:id,...`, typically `vars.APPLICATION_IDS`).
2. Reads the release version from the newest `<chart-name>-vX.Y.Z` git tag. If none exists yet, the publish step is skipped (not failed) — useful right after a chart's first commit, before any tag exists.
3. Publishes the version to the platform via [`glasskube/distr-create-version-action`](https://github.com/glasskube/distr-create-version-action). This step is best-effort (`continue-on-error: true`): a Lifecycle Management outage should not fail a chart release.

Charts that should never be registered (library charts, third-party dependency wrappers) are the caller's decision — gate the step itself with an `if:`, this composite has no chart-name allowlist/denylist baked in.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `chart-name` | Helm chart name (e.g. `plugin-access-manager`). Must have a matching entry in `application-ids` | Yes | — |
| `application-ids` | Application ID mappings in `chart:id[,chart:id...]` format (typically `vars.APPLICATION_IDS`) | Yes | — |
| `lifecycle-api-token` | API token for the Plugin Lifecycle Management platform | Yes | — |
| `working-directory` | Path to the chart directory (used to locate `values-template.yaml`) | Yes | — |
| `api-base` | Plugin Lifecycle Management API base URL | No | `https://lifecycle.lerian.studio/api/v1` |

## Usage as composite step

```yaml
- name: Publish Release in Plugin Lifecycle Management
  if: github.ref == 'refs/heads/main'
  uses: LerianStudio/github-actions-shared-workflows/src/deploy/lifecycle-management-publish@v1.x.x
  with:
    chart-name: ${{ matrix.chart.name }}
    application-ids: ${{ vars.APPLICATION_IDS }}
    lifecycle-api-token: ${{ secrets.LIFECYCLE_API_TOKEN }}
    working-directory: ${{ matrix.chart.working_dir }}
```

## Adding a new chart

1. Find the chart's **Application ID** in the Lifecycle Management (Distr) UI.
2. Add `chart-name:application-id` to the caller repository's `APPLICATION_IDS` repository variable (comma-separated if more than one chart).

## Required permissions

```yaml
permissions:
  contents: read # reads git tags for version resolution
```
