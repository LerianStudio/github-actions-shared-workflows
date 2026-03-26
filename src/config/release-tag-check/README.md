<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>release-tag-check</h1></td>
  </tr>
</table>

Compares the current latest semver (`v*`) tag against a snapshot captured by [`release-tag-snapshot`](../release-tag-snapshot/) to detect whether a new release was published. This is useful when the release action exits with failure due to post-release steps (e.g., backmerge plugin) but the release itself was successful.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `previous-tag` | The tag captured by `release-tag-snapshot` before the release step | Yes | |

## Outputs

| Output | Description |
|--------|-------------|
| `release-published` | `true` if a new tag was created since the snapshot, `false` otherwise |
| `release-version` | The new release version (without `v` prefix), empty if no new release |

## Usage as composite step

```yaml
- name: Snapshot tags before release
  id: pre-tags
  uses: LerianStudio/github-actions-shared-workflows/src/config/release-tag-snapshot@v1.x.x

- name: Semantic Release
  uses: cycjimmy/semantic-release-action@<sha> # v6
  id: semantic
  continue-on-error: true
  ...

- name: Check if release was published
  id: detect-release
  if: always() && steps.semantic.outcome == 'failure'
  uses: LerianStudio/github-actions-shared-workflows/src/config/release-tag-check@v1.x.x
  with:
    previous-tag: ${{ steps.pre-tags.outputs.latest-tag }}

- name: Backmerge PR fallback
  if: |
    always() && steps.semantic.outcome == 'failure' && (
      steps.semantic.outputs.new_release_published == 'true' ||
      steps.detect-release.outputs.release-published == 'true'
    )
  uses: LerianStudio/github-actions-shared-workflows/src/config/backmerge-pr@v1.x.x
  with:
    github-token: ${{ steps.app-token.outputs.token }}
    source-branch: ${{ github.ref_name }}
    version: ${{ steps.semantic.outputs.new_release_version || steps.detect-release.outputs.release-version }}
```

## Required permissions

```yaml
permissions:
  contents: read
```
