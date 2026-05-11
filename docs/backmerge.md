<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>backmerge</h1></td>
  </tr>
</table>

Configurable backmerge orchestrator. Receives a JSON list of source→target rules (literal or glob), expands globs against the remote, and delegates each resolved pair to the [`backmerge-sync`](../src/config/backmerge-sync/README.md) composite via matrix.

Decouples backmerge from semantic-release events. Suited for fan-out scenarios like `develop → develop-*` (one source, many integration branches).

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `rules` | JSON array of backmerge rules. See [Rules schema](#rules-schema). | Yes | |
| `pr_labels` | Default comma-separated labels for fallback PRs. Overridden per rule when `rules[].pr_labels` is set. | No | `""` |
| `dry_run` | Preview merges and PRs without applying changes. | No | `false` |

## Outputs

| Output | Description |
|--------|-------------|
| `has_pairs` | `"true"` when rule expansion resolved at least one source→target pair, `"false"` otherwise. Use to gate downstream jobs. |
| `matrix` | JSON object `{ "include": [...] }` listing every resolved pair. Always valid JSON — `{"include":[]}` when `has_pairs` is `"false"`. |

### Downstream gating example

```yaml
jobs:
  backmerge:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/backmerge.yml@develop
    with:
      rules: '[{ "from": "develop", "to": "develop-*" }]'
    secrets: inherit

  notify:
    needs: backmerge
    if: needs.backmerge.outputs.has_pairs == 'true'
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - run: echo "${{ needs.backmerge.outputs.matrix }}"
```

### Rules schema

Each entry in `rules` is an object:

| Field | Required | Description |
|-------|----------|-------------|
| `from` | Yes | Literal source branch (e.g. `develop`). |
| `to` | Yes | Literal target branch (e.g. `develop-fetcher`) **or** glob (`develop-*`). Globs are expanded against remote heads at runtime. |
| `mode` | No | `direct`, `pr`, or `direct-with-pr-fallback`. Default: `direct-with-pr-fallback`. |
| `commit_message` | No | Direct-merge commit message. Supports `${source}` / `${target}`. |
| `pr_title` | No | PR title template. Supports `${source}` / `${target}`. |
| `pr_labels` | No | Comma-separated labels overriding workflow-level `pr_labels`. |

## Required secrets

Pass via `secrets: inherit` from the caller workflow. Same set used by `release.yml`:

| Secret | Purpose |
|--------|---------|
| `LERIAN_STUDIO_MIDAZ_PUSH_BOT_APP_ID` | GitHub App credentials for an authenticated token (push + PR). |
| `LERIAN_STUDIO_MIDAZ_PUSH_BOT_PRIVATE_KEY` | |
| `LERIAN_CI_CD_USER_GPG_KEY` | GPG signing for the merge commit. |
| `LERIAN_CI_CD_USER_GPG_KEY_PASSWORD` | |
| `LERIAN_CI_CD_USER_NAME` | Git committer identity (must match GPG key for signature to be valid). |
| `LERIAN_CI_CD_USER_EMAIL` | |

## Required permissions in the caller job

```yaml
permissions:
  contents: write
  pull-requests: write
```

## Usage

### Fan-out `develop` into every `develop-*` on push

```yaml
name: Backmerge
on:
  push:
    branches: [develop]

jobs:
  backmerge:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/backmerge.yml@develop
    with:
      rules: |
        [
          { "from": "develop", "to": "develop-*", "mode": "direct-with-pr-fallback" }
        ]
    secrets: inherit
```

### Multi-rule: `main → develop` and `develop → develop-*`

```yaml
name: Backmerge
on:
  push:
    branches: [main, develop]

jobs:
  backmerge:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/backmerge.yml@develop
    with:
      rules: |
        [
          { "from": "main",    "to": "develop",   "mode": "direct-with-pr-fallback" },
          { "from": "develop", "to": "develop-*", "mode": "direct" }
        ]
      pr_labels: "backmerge,automation"
    secrets: inherit
```

> **Heads up:** the workflow does **not** filter rules by `github.ref` — every rule in `rules` runs on every invocation. The `merge-base --is-ancestor` short-circuit inside the composite makes irrelevant rules cheap (they exit as `skipped`), but if you want to scope which rules execute by trigger branch, gate the job in the caller:
>
> ```yaml
> jobs:
>   backmerge:
>     if: github.ref_name == 'main' || github.ref_name == 'develop'
>     uses: LerianStudio/github-actions-shared-workflows/.github/workflows/backmerge.yml@develop
>     with:
>       rules: ${{ github.ref_name == 'main'
>         && '[{ "from": "main", "to": "develop" }]'
>         || '[{ "from": "develop", "to": "develop-*" }]' }}
>     secrets: inherit
> ```

### Manual trigger with `workflow_dispatch`

```yaml
name: Self — Backmerge
on:
  workflow_dispatch:
    inputs:
      dry_run:
        type: boolean
        default: true

jobs:
  run:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/backmerge.yml@develop
    with:
      rules: |
        [{ "from": "develop", "to": "develop-*" }]
      dry_run: ${{ inputs.dry_run }}
    secrets: inherit
```

## Behavior

1. **Expand** — validates `rules` JSON, expands globs via `git ls-remote --heads`, builds a list of `(from, to, mode, …)` pairs. Pairs where `from == to` are dropped. Empty result short-circuits the workflow.
2. **Sync** — matrix job (`fail-fast: false`) running `backmerge-sync` per pair. Each pair is independent; one failure does not stop the others.
3. **Report** — every pair appends its outcome (`skipped`, `pushed`, `pr-opened`, `pr-existing`, `failed`, plus optional PR URL) to the workflow's job summary.

## Notes

- The workflow uses `secrets: inherit` style — secrets are referenced directly without being declared in `workflow_call.secrets:` (same pattern as `release.yml`).
- The GPG identity (`git_committer_name` / `git_committer_email`) and the composite's `git-user-name` / `git-user-email` are both bound to `LERIAN_CI_CD_USER_NAME` / `_EMAIL` so the merge-commit signature is valid.
- Glob expansion uses HTTPS `git ls-remote` against `${{ github.repository }}` — no checkout required in the `expand` job.
- The `[skip ci]` token is included in the default commit message to avoid retriggering CI on each target branch.
