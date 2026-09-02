<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>tier-promotion</h1></td>
  </tr>
</table>

Walks a stable release of this repository through the tier branches that downstream repositories pin their `uses:` to.

```text
main → stable tag → tier-0 → (approval) → tier-1 → (approval) → tier-2
```

**Internal-only.** The tier branches, the flow config and the Environments all live in this repository, so an external caller has no use for this workflow.

`self-release.yml` calls it after every stable release on `main`; `workflow_dispatch` covers manual promotions, resuming a failed tier, catching a lagging tier up, and rollbacks.

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

Dispatch the workflow with an **older** `tag`, scoped to the tiers you actually mean to move:

```text
Actions → Tier Promotion → Run workflow
  tag: v1.62.0
  only_tiers: tier-0
  dry_run: true        # confirm the plan, then re-run with false
```

The promotion lands as a new forward commit carrying the older tree, so `non_fast_forward` is never violated and no force push or ruleset bypass is needed. See [`only_tiers`](#only_tiers) for why leaving it empty during a rollback can move a lagging tier *forward*.

## Inputs

| Input | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `tag` | `string` | No | `""` | Stable tag to promote. Empty resolves the latest stable release. An older tag is the rollback path. |
| `config` | `string` | No | `config/tier-promotion.yml` | Path to the flow config |
| `only_tiers` | `string` | No | `""` | Comma-separated subset of tiers to promote, no spaces. Empty promotes the whole chain. |
| `dry_run` | `boolean` | No | `false` (`true` on dispatch) | Report each promotion without committing, pushing or opening a PR |

### `only_tiers`

Limits which tier jobs run. Excluded tiers are skipped, and the jobs after them tolerate a skipped predecessor (`!cancelled()` plus an explicit `success || skipped` check) while still refusing to run after a *failed* one.

Three situations call for it:

**Resuming a failed promotion.** A transient push failure on `tier-1` would otherwise mean re-running the whole chain, which reopens the `tier-2` approval for no reason. `only_tiers: tier-1` retries just that step.

**Catching a tier up.** An approval left pending dies after 30 days, leaving that tier behind. `only_tiers: tier-2` promotes only it.

**Scoping a rollback.** Promoting an older tag through the full chain does *not* simply move every tier back — a tier that was further behind than the target tag gets moved **forward** to it, ungated by any soak. Concretely:

```text
state:    tier-0=v1.63.0   tier-1=v1.62.0   tier-2=v1.60.0
intent:   roll tier-0 back to v1.62.0

full chain with tag=v1.62.0:
  tier-0 → v1.62.0   correct — rolled back
  tier-1 → v1.62.0   skipped — already carries that tree
  tier-2 → v1.60.0 → v1.62.0   advances two releases
```

The `tier-2` advance is gated by its approval, and `dry_run: true` (the dispatch default) would reveal it beforehand — but the approval screen only names the environment, so a reviewer cannot see it from there. `only_tiers: tier-0` removes the question.

The value is validated in the `resolve` job against the tiers declared in the config, so a typo fails the run instead of silently matching nothing and reporting success:

```text
::error::only_tiers must be a comma-separated list of tier branches with no spaces (e.g. 'tier-0' or 'tier-1,tier-2') — got 'tier-1, tier-2'
::error::only_tiers names 'tier-3', which is not declared in config/tier-promotion.yml (declared: tier-0 tier-1 tier-2)
```

## Secrets

Pass `secrets: inherit` from the caller.

| Secret | Required | Description |
|---|---|---|
| `LERIAN_STUDIO_MIDAZ_PUSH_BOT_APP_ID` | Yes | GitHub App client ID. The App's installation token pushes the promotion and opens the fallback PR |
| `LERIAN_STUDIO_MIDAZ_PUSH_BOT_PRIVATE_KEY` | Yes | GitHub App private key |
| `LERIAN_CI_CD_USER_GPG_KEY` | Yes | The `tier-rule` ruleset requires signed commits on `refs/heads/tier-*` |
| `LERIAN_CI_CD_USER_GPG_KEY_PASSWORD` | Yes | GPG passphrase |
| `LERIAN_CI_CD_USER_NAME` | Yes | Committer name (Lerian CI/CD identity) |
| `LERIAN_CI_CD_USER_EMAIL` | Yes | Committer email |

### Why a GitHub App and not a PAT

An App identity can be granted ruleset bypass on its own. That is what makes it possible to require a pull request on `refs/heads/tier-*` for everyone else while the promotion still pushes directly — the alternative was granting that exemption to a team of humans, which is the opposite of what the requirement is for.

It also has to be an App rather than `GITHUB_TOKEN`: a pull request opened by `GITHUB_TOKEN` does not trigger workflows, so the fallback PR would arrive with no checks and be unmergeable in any repository that gates on them.

The signing identity is separate and unchanged: commits are signed by the GPG key imported in the step after, because `tiers-rule` requires signed commits on the tier branches.

## Config and job chain must agree

The flow is declared in [`config/tier-promotion.yml`](../config/tier-promotion.yml), but the job chain in the workflow is written out **literally** — the `needs:` chain and each `environment:` are not interpolated from the config.

That is deliberate. GitHub Actions cannot build a job graph from data, and an `environment:` resolved through an expression could be pointed at an ungated environment by editing a config file, while a literal `environment: tier-1` is auditable by reading the workflow. An approval gate should not be indirect.

The cost is drift, so the `resolve` job compares the config against `EXPECTED_FLOW` and fails the run when they disagree:

```text
::error::config/tier-promotion.yml no longer matches the job chain in .github/workflows/tier-promotion.yml
::error::config:   tier-0:tier-0,tier-1:tier-1,tier-2:tier-2,tier-3:tier-3
::error::workflow: tier-0:tier-0,tier-1:tier-1,tier-2:tier-2
```

Adding or reordering a tier therefore means editing three things together: the config, the job chain, and `EXPECTED_FLOW`.

## Usage

### Automatic — every stable release

Wired in `self-release.yml`:

```yaml
jobs:
  promote-tiers:
    needs: publish-release
    if: >-
      github.ref == 'refs/heads/main'
      && needs.publish-release.result == 'success'
      && needs.publish-release.outputs.new_release_published == 'true'
    uses: ./.github/workflows/tier-promotion.yml
    with:
      tag: ${{ needs.publish-release.outputs.new_release_git_tag }}
      dry_run: false
    secrets: inherit
```

### Manual — dispatch

```text
Actions → Tier Promotion → Run workflow
  tag: v1.62.0        # empty = latest stable
  only_tiers:         # empty = whole chain
  dry_run: true       # default on dispatch
```

Two details there are load-bearing. The `new_release_published` gate: semantic-release exits **successfully** when a push carries no releasable commits, so gating on the job's result alone would open a train for a tag already sitting on the tiers and reopen its approvals. And passing `new_release_git_tag` explicitly rather than letting the controller re-resolve "latest stable", which would race a concurrent release.

## Not covered here

- **Self-reference rewriting.** The workflows in `.github/workflows/` carry absolute self-references (`uses: LerianStudio/github-actions-shared-workflows/src/...@v1`), so a consumer pinned to a tier still resolves those composites from `v1`. Rewriting them to the promoting tier is required for a tier to be a self-consistent channel, and is not part of this workflow yet.
- **Active canary validation.** Dispatching real workflow runs in canary repositories to prove a tier before the next one is promoted.

## Related

- [`config/tier-promotion.yml`](../config/tier-promotion.yml) — the flow
- [`src/config/tier-promote`](../src/config/tier-promote/README.md) — the composite that performs one promotion
- [`version-propagation.md`](version-propagation.md) — the pin-rewrite model that tiers are intended to replace
