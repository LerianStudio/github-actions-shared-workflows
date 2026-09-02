<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>Tier channels</h1></td>
  </tr>
</table>

How a release of this repository reaches the repositories that consume it, and how a consumer chooses when it wants to receive.

This page is for **consumers**. For the machinery that performs a promotion — the controller, the approval gates, rollback — see [`tier-promotion.md`](tier-promotion.md).

## What a tier is

A tier is a **branch of this repository**. You pin it in `uses:` instead of a version:

```yaml
jobs:
  ci:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-ci.yml@tier-1
    secrets: inherit
```

A release does not arrive because someone edited that line. It arrives when `tier-1` is **promoted** to carry it. The pin is set once, when the repository is onboarded, and is not touched again.

That inverts where the decision lives. Under version pins, "which release am I on" was answered by a commit in your repository, kept current by a bot opening one bump PR per release. Under tiers, it is answered by which branch you follow — and the promotion decision is made once, centrally, for every repository on that ring.

## The three tiers

| Tier | Who pins it | Receives | Gate |
|---|---|---|---|
| `@tier-0` | boilerplates, disposable repos, canaries | every stable release, immediately | none |
| `@tier-1` | most product repositories | after tier-0 has been accepted | human approval |
| `@tier-2` | shared libraries, regulatory services, plugins in production | after tier-1 has been accepted | human approval |

The tier you pin **is** your declaration of risk appetite. Nothing else records it, and there is no central list to keep in sync — changing tier is a one-line PR in your own repository.

When unsure between `tier-1` and `tier-2`, take `tier-2`. The conservative option should be the one nobody has to argue for.

### What the granularity actually buys

The rings are not three copies of the same thing on a delay. Each one exists to answer a different question:

**`tier-0` answers "does this run at all?"** It receives everything, unreviewed, so a change that is broken in an obvious way — a syntax error, a missing input, a composite that fails to load — surfaces here, in repositories where a red pipeline costs nothing. Its consumers are chosen for being disposable.

**`tier-1` answers "does this work in real work?"** It receives after someone looked at what tier-0 produced. Its consumers are ordinary product repositories, so a change that is subtly wrong — a check that passes when it should fail, a threshold that moved — shows up against real code and real reviews.

**`tier-2` answers "am I willing to bet production on it?"** It receives last, after tier-1 has lived with the change. Its consumers are the ones where a broken pipeline blocks a regulated deliverable or a published library.

A change that only ever exercised `tier-0` has been proven to *load*, not to be *correct*. That is the distinction the rings are for.

## The flow

```text
   ┌─ PR merged into develop ──────────────────────────────────┐
   │  beta release  v1.2.3-beta.N                             │
   │  reaches nobody: no consumer pins develop in production   │
   └──────────────────────────┬────────────────────────────────┘
                              │  develop → main
                              ▼
   ┌─ stable release on main ─ v1.2.3 ─────────────────────────┐
   │                                                           │
   │   promotion train opens, pinned to that tag               │
   │                                                           │
   │   tier-0  ──────────────────────►  promoted automatically │
   │      │                              consumers on tier-0   │
   │      │                              get it on their next  │
   │      │                              workflow run          │
   │      ▼                                                    │
   │   [approval: G_Github_Devops]                             │
   │      │                                                    │
   │   tier-1  ──────────────────────►  consumers on tier-1    │
   │      │                                                    │
   │      ▼                                                    │
   │   [approval: G_Github_Devops]                             │
   │      │                                                    │
   │   tier-2  ──────────────────────►  consumers on tier-2    │
   └───────────────────────────────────────────────────────────┘
```

Four properties of that flow are worth knowing as a consumer:

**Every tier receives the same commit.** The train resolves the tag to a commit once, when it opens. An approval granted three days later still promotes what was reviewed, not whatever `main` looks like at that moment.

**You receive on your next run, not at promotion time.** Moving a tier branch does not touch your repository. A run already in progress keeps the code it loaded; a repository whose CI is idle for a week keeps running the previous release until something triggers it.

**A newer release supersedes an older train waiting on the same tier.** If `v1.2.4` is cut while `v1.2.3` still sits unapproved at `tier-1`, approving promotes the newer one — the older train is dropped rather than promoted late.

**Rollback is forward-only.** An older release is promoted onto the tier as a new commit. Nothing is force-pushed and no history is rewritten, so a rollback is as auditable as a promotion.

## Choosing and changing your tier

Onboarding a repository: pin every `uses:` that points at this repository to the same tier. Mixing tiers within one repository is legal but means your PR validation and your release pipeline can be on different releases — avoid it unless you have a reason.

Changing tier later is a PR in your repository editing those lines. There is no ticket to open here and no central file to update.

```yaml
# before — receives on every stable release
uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-release.yml@tier-0

# after — receives only after tier-0 and tier-1 have been accepted
uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-release.yml@tier-2
```

## What tiers do not solve yet

**The composites inside a workflow are not yet channelled.** A reusable workflow in this repository calls its composite actions by absolute ref — mostly `@v1`, a floating major tag moved on every release — because `./` inside a reusable workflow resolves against the caller's workspace, not this repository. So pinning `@tier-2` today gates the workflow file you call, while the composites it invokes still arrive from the newest release.

The consequence is concrete: a tier controls *which orchestration* you run, not yet *all the code* that orchestration executes. Closing that gap means rewriting those refs to the promoting tier during promotion, and it is tracked as the next piece of work. Until then, treat the rings as reducing exposure rather than eliminating it.

**Reproducibility.** A branch ref is mutable by design, so re-running an old CI job may not execute the same code it executed the first time. This is the trade the model accepts in exchange for never editing a pin. It is not new — the `@v1` refs above already behaved this way.

## Related

- [`tier-promotion.md`](tier-promotion.md) — the controller, the gates, rollback
- [`../config/tier-promotion.yml`](../config/tier-promotion.yml) — the flow declaration
- [`version-propagation.md`](version-propagation.md) — the pin-rewrite model tiers replace, still running for repositories that pin a version
