<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>coderabbit-collapse</h1></td>
  </tr>
</table>

Folds a bot review's summary once every inline thread it opened is resolved, and restores it when one is reopened.

## The problem

A CodeRabbit review is two separate objects in the timeline:

```
coderabbitai reviewed 16 minutes ago
│
├── the summary        "Actionable comments posted: 2", warnings, walkthrough
│
├── thread  src/…/action.yml            ← finding 1
└── thread  src/…/action.yml (Outdated) ← finding 2
```

Resolving a thread hides that thread. Nothing hides the summary. So a pull request where every finding has been addressed and every thread resolved still opens on a block of bot text announcing two actionable comments that no longer exist — and on a pull request revised a few times, several of them stacked.

GitHub already offers the fix: **Hide comment** on the review, which minimises it as *resolved*. It is just manual, and nobody remembers to do it on the review they are no longer looking at.

## What this does

It automates that click, gated on the condition a human would apply: every thread the review opened has been resolved.

```
review PRR_… ─┬─ thread 1  isResolved: true
              └─ thread 2  isResolved: true    → minimizeComment(classifier: RESOLVED)
```

Reopen a thread and the summary comes back, because the review is relevant again.

The review → threads edge is not something the UI exposes, but GraphQL does. The **first** comment in a thread is the one that opened it, so its review is the parent:

```graphql
reviewThreads(first: 100) {
  nodes {
    isResolved
    comments(first: 1) { nodes { pullRequestReview { id } } }
  }
}
```

Later comments in a thread are replies and belong to other reviews — every reply posts a review of its own, bodyless, which is why those are skipped.

GraphQL and not REST for two independent reasons: only GraphQL reports `isMinimized`, so a REST-based pass could not distinguish a folded review from a fresh one and would refold everything on every event; and only GraphQL exposes a thread's parent review at all.

## Why the fold condition is a safeguard, not a convenience

`coderabbit-gate.yml` — which already minimises the superseded `@coderabbitai review` / *"Review finished"* comment pairs — carries this warning:

> Do not "improve" this by reaching into `reviews`: on PR #717 the review carrying CodeRabbit's permissions warning also carries 13 actionable findings, and the two are the same object.

That is the trap. A review body cannot be dismissed as noise, because the findings ride along with it. This workflow is the exception to that warning specifically because of what it refuses to do:

**A review with no inline thread is never folded.** Its fold condition can never be satisfied by resolving anything, so folding it would hide findings permanently, with no path back. That is exactly the PR #717 case, and it is skipped.

Everything else it leaves alone follows the same logic:

| Left alone | Why |
|------------|-----|
| reviews by authors outside `authors` | human reviews are not this workflow's business |
| bodyless reply reviews | nothing renders, so nothing hides |
| reviews minimised as `spam` / `off_topic` / `outdated` / `duplicate` | hidden for reasons unrelated to threads — undoing that is not this workflow's call |
| reviews with at least one unresolved thread | there is still something to read |

A failed mutation emits a `::warning::` and the job stays green. Tidying up is never worth a red check.

## Trigger, and the one GitHub does not offer

**There is no Actions trigger for resolving a review thread.** `pull_request_review_thread` exists as a webhook, carrying exactly the `resolved` and `unresolved` activity types this wants — but it is not an Actions event. It appears nowhere in `content/actions/reference/workflows-and-actions/events-that-trigger-workflows.md`; the family is `pull_request`, `pull_request_target`, `pull_request_review`, `pull_request_review_comment` and `pull_request_comment`, and nothing else. actionlint rejects it (`unknown Webhook event`), and a workflow declaring it simply never runs.

So the fold cannot follow the click. It rides on the next activity in the pull request instead:

```yaml
on:
  pull_request:
    types: [synchronize]          # a push
  pull_request_review:
    types: [submitted]            # a review landed
  pull_request_review_comment:
    types: [created]              # someone replied in a thread
```

**The cost is real and worth stating plainly: resolve the last thread, do nothing else, and the summary stays until something else happens on the pull request.** In practice something usually does — a push, the next review — and the fold catches up then. But this is a best-effort tidy, not a guarantee tied to the moment of resolution.

All three events run from the pull request's own merge ref (`refs/pull/N/merge`), not from the default branch, so a caller can test the workflow on the pull request that introduces it.

The alternative to all of this is a scheduled sweep over open pull requests, which would have full coverage at the cost of latency and of running from the default branch only — meaning it could not be tested before merging. That trade was considered and not taken.

A burst of activity fires the workflow several times over — a push and a review landing together is enough. Those runs must not race to the same mutation, so `concurrency` groups them per pull request and lets them run one at a time.

`cancel-in-progress: true` was the first instinct and it was wrong in practice: **a cancelled run is reported as a non-success check**, which leaves the pull request `UNSTABLE` over tidying that is cosmetic to begin with.

`false` does not remove cancellation, though — it moves it somewhere harmless, and it is worth being exact about which. GitHub keeps [at most one pending run per concurrency group](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency): *"any existing `pending` job or workflow in the same concurrency group will be canceled and the new queued job or workflow will take its place."* So a burst of three or more events still cancels the ones in the middle. What the setting does guarantee is that **no in-progress run is killed**, and that the last run queued — the one with the freshest view — is the one that survives.

Nothing is lost by that cancellation: every run reads the live thread state, so a superseded pending run would only have found the work already done. `queue: max` would hold up to 100 pending runs instead and remove cancellation entirely, but it is limited to newer Actions generations and is a workflow validation error where it is not available — too much risk to take on for cosmetic tidying.

## Usage

```yaml
name: Collapse Resolved Reviews

on:
  pull_request:
    types: [synchronize]
  pull_request_review:
    types: [submitted]
  pull_request_review_comment:
    types: [created]

permissions:
  contents: read
  pull-requests: write

concurrency:
  group: coderabbit-collapse-${{ github.event.pull_request.number }}
  cancel-in-progress: false

jobs:
  collapse:
    # Fork pull requests get a read-only token and no secrets, so this could never fold
    # anything there — and the checked-out composite would be the contributor's code.
    if: github.event.pull_request.head.repo.full_name == github.repository
    permissions:
      contents: read
      pull-requests: write
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/coderabbit-collapse.yml@tier-1
    with:
      pr_number: ${{ github.event.pull_request.number }}
    secrets: inherit
```

## Outputs

| Output | Description |
|--------|-------------|
| `has_changes` | `true` when this run changed anything — any review folded or restored. Always `false` under `dry_run`. |

The composite behind it also exposes `evaluated`, `collapsed` and `restored`. The last two count mutations that landed, so a non-zero value is a real state change; a dry-run reports its plan in the job summary, never in those counters.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `pr_number` | Pull request to act on | Yes | |
| `authors` | Comma-separated logins whose reviews are eligible. A trailing `[bot]` is optional — REST and GraphQL disagree on it, so both spellings match. | No | `coderabbitai[bot]` |
| `dry_run` | Report the decision without mutating the pull request | No | `false` |
| `runner_type` | Runner label for the job | No | `blacksmith-4vcpu-ubuntu-2404` |

## Secrets

| Secret | Description | Required |
|--------|-------------|----------|
| `MANAGE_TOKEN` | Token with `pull-requests: write`. Falls back to `github.token`, which is enough for same-repository pull requests — the default token is read-only on pull requests from forks. | No |

## Permissions

```yaml
permissions:
  contents: read
  pull-requests: write
```

`pull-requests: write` is what `minimizeComment` needs to fold a comment authored by someone else.

## Related

- [`coderabbit-gate`](coderabbit-gate.md) — decides which pull requests get reviewed, and folds the superseded request/echo comment pairs
- [`src/notify/coderabbit-collapse`](../src/notify/coderabbit-collapse/README.md) — the composite action, its inputs and outputs
