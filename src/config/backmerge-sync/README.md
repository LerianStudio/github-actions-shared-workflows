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
| `pr-labels` | Comma-separated labels applied to the PR opened in `pr` or fallback mode. Empty by default — only opt in to labels that exist in the caller repo. | No | `""` |
| `git-user-name` | Git `user.name` for the merge commit | No | `github-actions[bot]` |
| `git-user-email` | Git `user.email` for the merge commit | No | `41898282+github-actions[bot]@users.noreply.github.com` |
| `dry-run` | Preview actions without pushing or opening PRs | No | `false` |

## Outputs

| Output | Description |
|--------|-------------|
| `action` | One of `skipped`, `pushed`, `pr-opened`, `pr-existing`, `failed` |
| `pr-url` | URL of the PR opened or reused in `pr` or fallback mode (empty when no PR was created) |
| `pr-number` | Number of the PR opened or reused in `pr` or fallback mode (empty when no PR was created) |

## Modes

| Mode | Behavior |
|------|----------|
| `direct` | Merge and push. Fails the step on conflict or rejected push. No PR is opened. |
| `pr` | Always open (or reuse) a PR from a temporary branch into `target-branch`. Never pushes directly. |
| `direct-with-pr-fallback` | Try direct merge & push first. On conflict or rejection, fall back to opening a PR. |

If the target branch already contains the source (`merge-base --is-ancestor`), the step is a no-op and outputs `action=skipped`.

## The temporary branch

The PR is opened from `backmerge/<source>-to-<target>-<hash>`, not from `source-branch` itself.

Resolving a conflict means committing on the head branch. With `main` as the head that commit is forbidden by the branch ruleset, so the PR opens in a state nobody can finish — the only way out is a bypass. It also forces consumers to authorise `main` and `release-candidate` as promotion sources, and the rule then cannot tell an automated backmerge from one a person opened by hand.

The name is **deterministic**, never per-run: the reuse lookup finds the open PR by head, so a changing name would open one PR per run and leave orphaned branches behind. `/` is flattened to `-` and a 6-character digest of the pair is appended, so `hotfix/x` and `hotfix-x` do not collide.

### It is never force-updated while a PR is open

That branch is where the human conflict resolution lives.

| State | Behavior |
|---|---|
| No open PR for the pair | Reset the branch to the source tip, open the PR |
| Open PR exists | Merge the source tip **into** the branch, preserving earlier resolutions. Clean → push, the PR updates itself. Conflict → leave the branch untouched and upsert a sticky comment saying commits are pending |

The open PR accumulates the backlog for its pair instead of multiplying PRs or rewriting reviewed history.

### Migrating

A backmerge PR opened before this behavior has `head = <source>`. The composite reuses it rather than opening a duplicate, and warns that it should be closed — its conflicts still cannot be resolved without writing to a protected branch. Close the old ones and the next run opens replacements from the temporary branch.

Cleanup needs no configuration: `backmerge/*` matches none of `branch-cleanup`'s protected patterns, so the `routine.yml` post-merge hook deletes it like any other head branch.

## Usage as composite step

```yaml
- name: Checkout
  uses: actions/checkout@v4
  with:
    fetch-depth: 0
    persist-credentials: true   # required for direct push

- name: Sync develop into develop-fetcher
  uses: LerianStudio/github-actions-shared-workflows/src/config/backmerge-sync@v1
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
          persist-credentials: true
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
- Labels passed via `pr-labels` are filtered against the caller repo's existing labels — entries that do not exist are skipped with a `::warning::` rather than failing the PR creation.
