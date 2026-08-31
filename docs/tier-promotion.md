<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>tier-promotion</h1></td>
  </tr>
</table>

Walks a stable release of this repository through the tier branches that downstream repositories pin their `uses:` to.

```
main → stable tag → tier-0 → (approval) → tier-1 → (approval) → tier-2
```

**Internal-only.** The tier branches, the flow config and the Environments all live in this repository, so an external caller has no use for this workflow. `self-release.yml` is the intended entrypoint; `workflow_dispatch` covers manual promotions, re-runs and rollbacks.

## Why tiers are branches

A consumer pins a tier once and never edits that pin again:

```yaml
jobs:
  ci:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-ci.yml@tier-1
```

Which tier a repository pins **is** its declaration of how fast it wants to receive. Changing tier is a PR in that repository, not an entry in a central list.

## What a promotion actually does

A promotion is a **commit on the tier branch** — never a ref move, never a merge.

| Not this | Why |
|---|---|
| Ref move | The `tier-rule` ruleset blocks `non_fast_forward` on `refs/heads/tier-*`; a moved ref may not be a fast-forward. A commit on top of the tip always is. |
| Merge | Once the tier branches carry content that differs from `main`, a merge conflicts on exactly the lines that differ, on every promotion, forever. |

Instead the promoted tree is materialized wholesale onto the tier tip with `git read-tree`, producing one commit whose tree **is** the promoted tree. No conflict is possible by construction.

Direct push first; on failure, the promotion falls back to a PR into the tier branch — the same mechanic `version-propagation.yml` uses against consumer repositories.

## The train

The tag is resolved to a commit **once**, in the `resolve` job. Every tier promotes that exact SHA, so an approval granted days later still promotes what was reviewed rather than whatever `main` looks like at that moment.

Two gates run before anything is written:

- The tag must be a stable semver (`^v\d+\.\d+\.\d+$`). Pre-releases are refused.
- The commit must be an ancestor of `origin/main`. Promoting something that never landed there would put code into a tier branch that no review ever saw.

## Concurrency and superseded trains

Each tier has its **own** concurrency group with `cancel-in-progress: false`.

Sharing one group would park a `tier-0` promotion behind an approval pending on `tier-1`, which inverts the purpose of `tier-0`. And because a concurrency group holds at most one pending run, a newer release supersedes an older train still waiting on the same tier. That is wanted: the newer commit is a superset, and approving a superseded train would promote something that never soaked.

## Rollback

Dispatch the workflow with an **older** `tag`. The promotion lands as a new forward commit carrying the older tree, so `non_fast_forward` is never violated and no force push or ruleset bypass is needed.

## Inputs

| Input | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `tag` | `string` | No | `""` | Stable tag to promote. Empty resolves the latest stable release. An older tag is the rollback path. |
| `config` | `string` | No | `config/tier-promotion.yml` | Path to the flow config |
| `dry_run` | `boolean` | No | `false` (`true` on dispatch) | Report each promotion without committing, pushing or opening a PR |

## Secrets

Pass `secrets: inherit` from the caller.

| Secret | Required | Description |
|---|---|---|
| `MANAGE_TOKEN` | Yes | Pushes the promotion and opens the fallback PR. A PAT rather than `GITHUB_TOKEN` on purpose: a PR opened by `GITHUB_TOKEN` does not trigger workflows, which would leave a fallback PR with no checks and therefore unmergeable. |
| `LERIAN_CI_CD_USER_GPG_KEY` | Yes | The `tier-rule` ruleset requires signed commits on `refs/heads/tier-*` |
| `LERIAN_CI_CD_USER_GPG_KEY_PASSWORD` | Yes | GPG passphrase |
| `LERIAN_CI_CD_USER_NAME` | Yes | Committer name (Lerian CI/CD identity) |
| `LERIAN_CI_CD_USER_EMAIL` | Yes | Committer email |

## Config and job chain must agree

The flow is declared in [`config/tier-promotion.yml`](../config/tier-promotion.yml), but the job chain in the workflow is written out **literally** — the `needs:` chain and each `environment:` are not interpolated from the config.

That is deliberate. GitHub Actions cannot build a job graph from data, and an `environment:` resolved through an expression could be pointed at an ungated environment by editing a config file, while a literal `environment: tier-1` is auditable by reading the workflow. An approval gate should not be indirect.

The cost is drift, so the `resolve` job compares the config against `EXPECTED_FLOW` and fails the run when they disagree:

```
::error::config/tier-promotion.yml no longer matches the job chain in .github/workflows/tier-promotion.yml
::error::config:   tier-0:tier-0,tier-1:tier-1,tier-2:tier-2,tier-3:tier-3
::error::workflow: tier-0:tier-0,tier-1:tier-1,tier-2:tier-2
```

Adding or reordering a tier therefore means editing three things together: the config, the job chain, and `EXPECTED_FLOW`.

## Usage

Wired into `self-release.yml`:

```yaml
jobs:
  promote-tiers:
    needs: publish-release
    if: github.ref == 'refs/heads/main' && needs.publish-release.result == 'success'
    uses: ./.github/workflows/tier-promotion.yml
    with:
      tag: ""
      dry_run: false
    secrets: inherit
```

Manual promotion or rollback:

```
Actions → Tier Promotion → Run workflow
  tag: v1.62.0        # empty = latest stable; older tag = rollback
  dry_run: true       # default on dispatch
```

## Not covered here

- **Self-reference rewriting.** The workflows in `.github/workflows/` carry absolute self-references (`uses: LerianStudio/github-actions-shared-workflows/src/...@v1`), so a consumer pinned to a tier still resolves those composites from `v1`. Rewriting them to the promoting tier is required for a tier to be a self-consistent channel, and is not part of this workflow yet.
- **Active canary validation.** Dispatching real workflow runs in canary repositories to prove a tier before the next one is promoted.

## Related

- [`config/tier-promotion.yml`](../config/tier-promotion.yml) — the flow
- [`src/config/tier-promote`](../src/config/tier-promote/README.md) — the composite that performs one promotion
- [`version-propagation.md`](version-propagation.md) — the pin-rewrite model that tiers are intended to replace
