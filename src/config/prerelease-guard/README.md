<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>prerelease-guard</h1></td>
  </tr>
</table>

Fails the run if a calculated beta/rc version's `X.Y.Z` has already been published as a stable release. Used as a defensive check in `release.yml`, after a `semantic-release` dry-run on a prerelease branch (`develop`, `release-candidate`), to catch cases where the branch is still out of sync with the stable branch even after the pre-sync gate — for example concurrent pushes, or a pending backmerge PR that was merged manually without re-triggering the release.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `calculated-version` | The prerelease version `semantic-release` would publish (e.g. `1.10.0-beta.6`) | Yes | |
| `source-branch` | Name of the stable branch the prerelease is compared against (for the error message only) | No | `main` |
| `target-branch` | Name of the prerelease branch being validated (for the error message only). Defaults to the current ref if omitted. | No | `''` |

## Outputs

None. The action exits non-zero (failing the job) when the calculated prerelease's `X.Y.Z` is not strictly newer than the highest stable tag already published.

## Usage as composite step

```yaml
- name: Determine next version (dry-run)
  id: semantic_dry
  uses: cycjimmy/semantic-release-action@<sha> # v6
  with:
    ci: false
    dry_run: true
    working_directory: ${{ matrix.app.working_dir }}

- name: Guard against stale prerelease
  if: steps.semantic_dry.outputs.new_release_published == 'true'
  uses: LerianStudio/github-actions-shared-workflows/src/config/prerelease-guard@v1.x.x
  with:
    calculated-version: ${{ steps.semantic_dry.outputs.new_release_version }}
    source-branch: ${{ inputs.backmerge_source }}
    target-branch: ${{ github.ref_name }}
```

## Required permissions

```yaml
permissions:
  contents: read
```
