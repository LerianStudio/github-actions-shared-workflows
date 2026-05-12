<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>version-propagation</h1></td>
  </tr>
</table>

Composite action that propagates a new `LerianStudio/github-actions-shared-workflows` release to the downstream repositories declared in [`config/version-propagation.yml`](../../../config/version-propagation.yml).

For each resolved target, it rewrites `@vX.Y.Z` pins inside `.github/workflows/*.yml` and either pushes directly to `target_branch` or opens a PR (fallback on failure; mandatory for `major` bumps).

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `new-tag` | Tag to propagate. Must match `^v\d+\.\d+\.\d+$`. | Yes | — |
| `previous-tag` | Previous tag, used to compute the bump level. Empty resolves the last published release via `gh release list`. | No | `""` |
| `config` | Path to the propagation matrix in this repo. | No | `config/version-propagation.yml` |
| `target-filter` | CSV of `owner/name` to restrict the run to a subset. | No | `""` |
| `dry-run` | Print the diff and intended action per target, do not push or open PRs. | No | `"false"` |
| `github-token` | GitHub App token with `contents:write`, `pull-requests:write`, `workflows:write` on every target repo. | Yes | — |

## Matrix file format

Repository-keyed map at `config/version-propagation.yml`. Each `owner/name` is a key; the value block holds per-repo overrides. Empty block (`{}`) means "use all defaults".

```yaml
version: 1

defaults:
  target_branch: develop
  workflow_files:
    - "*.yml"
  auto_merge_pr_fallback:
    patch: true
    minor: false
    major: false
  enabled: true

repositories:
  LerianStudio/go-boilerplate-ddd:
    target_branch: main          # trunk-based

  LerianStudio/midaz: {}         # inherits all defaults (gitflow on develop)

  LerianStudio/plugin-fees:
    workflow_files:
      - "build.yml"
      - "release.yml"
      - "pr-*.yml"
    auto_merge_pr_fallback:
      patch: true
      minor: true                # opt-in to minor auto-merge
      major: false

  LerianStudio/legacy-service:
    enabled: false               # temporarily pause without removing
```

Per-repo keys (all optional):

| Key | Effect |
|---|---|
| `target_branch` | Branch where the bump is applied |
| `workflow_files` | Glob list restricting which workflow files are touched |
| `auto_merge_pr_fallback` | Per-bump-level toggle for `gh pr merge --auto --squash` on PR fallback |
| `enabled` | `false` skips the repo without removing the entry |

## Usage

### As a composite action (inline step)

```yaml
jobs:
  propagate:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v6
        with:
          ref: ${{ inputs.new_tag }}

      - name: Import GPG key for signed commits
        uses: crazy-max/ghaction-import-gpg@v7
        with:
          gpg_private_key: ${{ secrets.LERIAN_CI_CD_USER_GPG_KEY }}
          passphrase: ${{ secrets.LERIAN_CI_CD_USER_GPG_KEY_PASSWORD }}
          git_committer_name: ${{ secrets.LERIAN_CI_CD_USER_NAME }}
          git_committer_email: ${{ secrets.LERIAN_CI_CD_USER_EMAIL }}
          git_config_global: true
          git_user_signingkey: true
          git_commit_gpgsign: true

      - uses: LerianStudio/github-actions-shared-workflows/src/config/version-propagation@v1.29.0
        with:
          new-tag: ${{ inputs.new_tag }}
          github-token: ${{ secrets.MANAGE_TOKEN }}
```

### As a reusable workflow (internal)

The reusable wrapper `version-propagation.yml` is internal to this repo (it reads `config/version-propagation.yml` which lives here). It is called from `self-release.yml` — see [When to run](#when-to-run) below. External callers should not use it directly.

### Dry run (preview only)

```yaml
# Use @develop or your feature branch to test before releasing
- uses: LerianStudio/github-actions-shared-workflows/src/config/version-propagation@develop
  with:
    new-tag: v1.29.0
    target-filter: LerianStudio/go-boilerplate-ddd
    dry-run: "true"
    github-token: ${{ secrets.MANAGE_TOKEN }}
```

## Permissions required

The composite only reads its own repo. The **token passed via `github-token`** carries the write permissions and must hold, on every target repo:

```yaml
contents: write
pull-requests: write
workflows: write     # required by GitHub for edits inside .github/workflows/
```

In the canonical setup, this token is `secrets.MANAGE_TOKEN` (the same PAT used by `gitops-update.yml`). The calling workflow only needs `contents: read`.

## When to run

This composite is intended to run as the final leg of the release pipeline — see [`self-release.yml`](../../../.github/workflows/self-release.yml), which adds a `propagate-version` job after `publish-release` on `main`:

```yaml
propagate-version:
  needs: publish-release
  if: github.ref == 'refs/heads/main' && needs.publish-release.result == 'success'
  uses: ./.github/workflows/version-propagation.yml
  with:
    new_tag: ""      # auto-resolves the just-published stable tag
    dry_run: false
  secrets: inherit
```

See [`docs/version-propagation.md`](../../../docs/version-propagation.md) for the full end-to-end overview and troubleshooting.
