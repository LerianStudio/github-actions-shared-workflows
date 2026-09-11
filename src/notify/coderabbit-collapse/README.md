<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>coderabbit-collapse</h1></td>
  </tr>
</table>

Minimises a bot review's summary once every inline thread it opened is resolved, and restores it when one is reopened.

A CodeRabbit review is two things in the timeline: a summary block (*"Actionable comments posted: 2"*, plus whatever warnings it has for you) and the inline threads carrying the findings. Resolving the threads hides them, but the summary stays — so a pull request that has addressed everything still opens on a wall of bot text with nothing actionable left in it.

This action folds the summary when, and only when, its own children are all resolved. Folding preserves history: the review remains, one click from being expanded.

## How it works

The review → threads edge is the part the UI never shows. GraphQL does:

```graphql
reviewThreads(first: 100) {
  nodes {
    isResolved
    comments(first: 1) { nodes { pullRequestReview { id } } }   # ← the parent
  }
}
```

The **first** comment in a thread is the one that opened it, so its review is the parent. Later comments are replies and may belong to other reviews — every reply posts a review of its own.

With threads grouped by parent, each eligible review takes one of four paths:

| Condition | Action |
|-----------|--------|
| every child thread resolved | `minimizeComment(classifier: RESOLVED)` |
| already minimised, children still all resolved | nothing — the fold is idempotent |
| a child reopened, and the review was folded as `resolved` | `unminimizeComment` |
| a child reopened, and the review was hidden for any other reason | nothing |

GraphQL rather than REST for two independent reasons: only GraphQL reports `isMinimized`, so a REST-based pass could not tell a folded review from a fresh one and would refold everything on every run; and only GraphQL exposes the review a thread belongs to.

### What it will not touch

**A review with no inline thread is never folded.** This is deliberate and load-bearing. [`coderabbit-gate`](../../../.github/workflows/coderabbit-gate.yml) carries a warning earned on PR #717: the review that held CodeRabbit's permissions notice also held 13 actionable findings, because *a summary and its findings are the same object*. Folding a review whose fold condition can never be satisfied would hide findings for good. Requiring at least one resolvable child is what makes this action the safe exception to that warning rather than a violation of it.

It also leaves alone: reviews by authors outside `authors`; bodyless reply reviews (nothing renders, so nothing hides); and anything minimised as `spam`, `off_topic`, `outdated` or `duplicate` — hidden for reasons that have nothing to do with threads.

A failed mutation is a `::warning::`, never a failed job. Tidying is not worth a red check.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `github-token` | GitHub token with pull-requests write permission | Yes | |
| `pr-number` | Pull request to act on | Yes | |
| `authors` | Comma-separated logins whose reviews are eligible. A trailing `[bot]` is optional — REST and GraphQL disagree on it, so both spellings match. | No | `coderabbitai[bot]` |
| `dry-run` | When true, report what would be folded without mutating the pull request | No | `false` |

## Outputs

| Output | Description |
|--------|-------------|
| `evaluated` | Number of eligible reviews examined |
| `collapsed` | Number of reviews minimised in this run |
| `restored` | Number of reviews unminimised because a thread was reopened |

## Usage as composite step

```yaml
jobs:
  collapse:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    permissions:
      pull-requests: write
    steps:
      - name: Collapse resolved CodeRabbit reviews
        uses: LerianStudio/github-actions-shared-workflows/src/notify/coderabbit-collapse@v1.x.x
        with:
          github-token: ${{ secrets.MANAGE_TOKEN || github.token }}
          pr-number: ${{ github.event.pull_request.number }}
```

## Usage as reusable workflow

GitHub has no Actions trigger for resolving a review thread — `pull_request_review_thread` is a webhook only, not an Actions event — so the fold rides on the next activity in the pull request instead. Resolve the last thread and do nothing else, and the summary stays until something else happens there:

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

jobs:
  collapse:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/coderabbit-collapse.yml@v1.x.x
    with:
      pr_number: ${{ github.event.pull_request.number }}
    secrets: inherit
```

See [`docs/coderabbit-collapse.md`](../../../docs/coderabbit-collapse.md).

## Required permissions

```yaml
permissions:
  contents: read
  pull-requests: write
```

`pull-requests: write` is what `minimizeComment` needs to fold a comment written by someone else. For pull requests from forks the default `GITHUB_TOKEN` is read-only, so pass a `MANAGE_TOKEN` if fork pull requests are in scope.

## Tests

```bash
python3 src/notify/coderabbit-collapse/test.py
```
