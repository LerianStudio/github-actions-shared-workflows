<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>release-tag-snapshot</h1></td>
  </tr>
</table>

Captures the latest semver (`v*`) tag before a release step runs. Used together with [`release-tag-check`](../release-tag-check/) to detect whether a new release was published — even when the release action reports failure due to post-release steps (e.g., backmerge).

## Inputs

None.

## Outputs

| Output | Description |
|--------|-------------|
| `latest-tag` | The latest `v*` tag before the release step, or `none` if no tags exist |

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
```

## Required permissions

```yaml
permissions:
  contents: read
```
