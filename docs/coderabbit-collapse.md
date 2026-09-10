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

## Trigger

`pull_request_review_thread` is what makes this useful:

```yaml
on:
  pull_request_review_thread:
    types: [resolved, unresolved]
```

The event fires the moment a thread changes state, so the fold follows the click. Driving it from `pull_request` instead would fold on the *next push* — the one moment the summary is actually worth reading.

Resolving several threads in a row fires the workflow once per click. Only the last run matters, since each one reads the live state of every thread, so `concurrency` with `cancel-in-progress: true` drops the earlier ones instead of letting them race to the same mutation.

## Usage

```yaml
name: Collapse Resolved Reviews

on:
  pull_request_review_thread:
    types: [resolved, unresolved]

permissions:
  contents: read
  pull-requests: write

concurrency:
  group: coderabbit-collapse-${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  collapse:
    permissions:
      contents: read
      pull-requests: write
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/coderabbit-collapse.yml@v1.x.x
    with:
      pr_number: ${{ github.event.pull_request.number }}
    secrets: inherit
```

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
