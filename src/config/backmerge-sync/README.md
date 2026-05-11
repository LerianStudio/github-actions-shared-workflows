<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>backmerge-sync</h1></td>
  </tr>
</table>

Syncs a source branch into a target branch via direct push, pull request, or direct-with-PR-fallback. Designed for keeping long-lived integration branches (e.g., `develop-*`) in sync with their parent (`develop`).

Single source → single target. For fan-out across multiple targets (e.g., `develop` → every `develop-*`), call this composite from a matrix in the consuming workflow.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `github-token` | GitHub token with `contents:write` and `pull-requests:write` | Yes | |
| `source-branch` | Branch to merge from | Yes | |
| `target-branch` | Branch to merge into | Yes | |
| `mode` | `direct`, `pr`, or `direct-with-pr-fallback` | No | `direct-with-pr-fallback` |
| `commit-message` | Direct-merge commit message. Supports `${source}` / `${target}` | No | `chore(backmerge): sync ${source} into ${target} [skip ci]` |
| `pr-title` | Fallback PR title. Supports `${source}` / `${target}` | No | `chore(backmerge): sync ${source} → ${target}` |
| `pr-labels` | Comma-separated labels for the fallback PR | No | `backmerge,automation` |
| `git-user-name` | Git `user.name` for the merge commit | No | `github-actions[bot]` |
| `git-user-email` | Git `user.email` for the merge commit | No | `41898282+github-actions[bot]@users.noreply.github.com` |
| `dry-run` | Preview actions without pushing or opening PRs | No | `false` |

## Outputs

| Output | Description |
|--------|-------------|
| `action` | One of `skipped`, `pushed`, `pr-opened`, `pr-existing`, `failed` |
| `pr-url` | URL of the fallback PR (empty when no PR was created) |
| `pr-number` | Number of the fallback PR (empty when no PR was created) |

## Modes

| Mode | Behavior |
|------|----------|
| `direct` | Merge and push. Fails the step on conflict or rejected push. No PR is opened. |
| `pr` | Always open (or reuse) a PR from `source-branch` into `target-branch`. Never pushes directly. |
| `direct-with-pr-fallback` | Try direct merge & push first. On conflict or rejection, fall back to opening a PR. |

If the target branch already contains the source (`merge-base --is-ancestor`), the step is a no-op and outputs `action=skipped`.

## Usage as composite step

```yaml
- name: Checkout
  uses: actions/checkout@v4
  with:
    fetch-depth: 0
    persist-credentials: true   # required for direct push

- name: Sync develop into develop-fetcher
  uses: LerianStudio/github-actions-shared-workflows/src/config/backmerge-sync@v1.x.x
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    source-branch: develop
    target-branch: develop-fetcher
    mode: direct-with-pr-fallback
```

## Usage with matrix fan-out

```yaml
jobs:
  fanout:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    permissions:
      contents: write
      pull-requests: write
    strategy:
      fail-fast: false
      matrix:
        target: [develop-fetcher, develop-matcher, develop-product]
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: LerianStudio/github-actions-shared-workflows/src/config/backmerge-sync@v1.x.x
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          source-branch: develop
          target-branch: ${{ matrix.target }}
```

## Required permissions

```yaml
permissions:
  contents: write
  pull-requests: write
```

The caller must run `actions/checkout` with `fetch-depth: 0` and `persist-credentials: true` before invoking this composite — direct pushes rely on credentials configured by the checkout step.

## Notes

- Idempotent: re-running with an already-merged target outputs `skipped`; re-running after a fallback PR was opened outputs `pr-existing`.
- `dry-run: true` logs every intended action via `::notice::` annotations without pushing or calling `gh pr create`.
- `[skip ci]` is included in the default commit message to avoid re-triggering CI on the target branch. Override `commit-message` to change this.
