<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>non-doc-changes</h1></td>
  </tr>
</table>

Detects whether a pull request or push contains changes beyond documentation/meta files. Use it to gate expensive pipelines (analysis, security, release) so documentation-only changes don't trigger a full run.

It auto-detects the event:

- `pull_request` / `pull_request_target` — lists changed files via `gh api repos/{repo}/pulls/{n}/files` (removed files excluded).
- `push` — diffs `before...after` via `gh api repos/{repo}/compare`. A first push (empty/zero base ref) returns `code=true`.

A changed file "counts" unless it matches one of the `ignore-globs` patterns. If every changed file matches an ignore pattern, `code=false`.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `github-token` | GitHub token for gh CLI access (read on contents and pull requests) | Yes | |
| `ignore-globs` | Space-separated glob patterns treated as documentation/meta | No | `*.md docs/* .github/* LICENSE* .gitignore` |

## Outputs

| Output | Description |
|--------|-------------|
| `code` | `true` when at least one changed file is not matched by `ignore-globs`; `false` otherwise |

## Usage as composite step

```yaml
jobs:
  changes:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    outputs:
      code: ${{ steps.gate.outputs.code }}
    steps:
      - name: Non-doc change gate
        id: gate
        uses: LerianStudio/github-actions-shared-workflows/src/config/non-doc-changes@v1
        with:
          github-token: ${{ github.token }}
          ignore-globs: "*.md docs/* .github/* LICENSE* .gitignore"
```

## Required permissions

```yaml
permissions:
  contents: read
  pull-requests: read
```
