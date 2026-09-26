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

## Build identity verification

The release that carries build identity verification changes what a build run does just before it pushes an image. Promotion is unaffected — the train above delivers it like any other release — but what it does to you depends on your Dockerfile, not on your tier.

**Your Dockerfile declares `ARG REVISION`.** CI builds an image for the runner's native platform, asks it `docker run <image> --version`, and refuses to push when the version or the commit the binary reports disagrees with what the release injected. An image whose identity disagrees fails the build instead of publishing a lying image. Losing `ARG REVISION` itself is a different regression: through `go-release.yml` it always fails the build of the primary image, and fails an `extra_builds` group unless the group, or the caller's top-level input, sets `require_build_identity: false`; a direct caller of `build.yml` fails only when it sets `require_build_identity: true`, and otherwise gets the warning below. The check is a step inside `build.yml` itself, not a composite, so it arrives with the workflow file your tier pins and is not subject to the composite gap described below.

**It does not** — check with `grep -nE '^[[:space:]]*[Aa][Rr][Gg][[:space:]]+REVISION([[:space:]]|=|$)' <your dockerfile>`, the same match the build uses. A declaration whose name only starts with `REVISION`, such as `ARG REVISION_ID`, does not count. For the primary image of a `go-release.yml` caller the build fails, pointing at the contract. Wherever the flag is off (an `extra_builds` group or its caller set to `false`, or a direct `build.yml` caller without the input) the build proceeds exactly as before and the job emits one warning naming the image.

Adopting is three `ARG` lines in the Dockerfile and three variables in `main`: [build.md, Build identity contract](build.md#build-identity-contract).

The warning path let a `tier-0` promotion, which needs no human approval, reach repositories that had not adopted yet. For the primary image of a `go-release.yml` caller it is gone: a repository on a tier meets the rule at the promotion that carries it, a fixed-pin consumer on its next bump. Adopt before either.

## What tiers do not solve yet

**The composites inside a workflow are not yet channelled.** A reusable workflow in this repository calls its composite actions by absolute ref — mostly `@v1`, a floating major tag moved on every release — because `./` inside a reusable workflow resolves against the caller's workspace, not this repository. So pinning `@tier-2` today gates the workflow file you call, while the composites it invokes still arrive from the newest release.

The consequence is concrete: a tier controls *which orchestration* you run, not yet *all the code* that orchestration executes. Closing that gap means rewriting those refs to the promoting tier during promotion, and it is tracked as the next piece of work. Until then, treat the rings as reducing exposure rather than eliminating it.

**Reproducibility.** A branch ref is mutable by design, so re-running an old CI job may not execute the same code it executed the first time. This is the trade the model accepts in exchange for never editing a pin. It is not new — the `@v1` refs above already behaved this way.

## Related

- [`tier-promotion.md`](tier-promotion.md) — the controller, the gates, rollback
- [`../config/tier-promotion.yml`](../config/tier-promotion.yml) — the flow declaration
- [`version-propagation.md`](version-propagation.md) — the pin-rewrite model tiers replaced; now disabled, kept as the rollback path
