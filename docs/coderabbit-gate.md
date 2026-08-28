<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>coderabbit-gate</h1></td>
  </tr>
</table>

Gates CodeRabbit reviews on CI, and declares which pull requests are in scope.

Without a gate, CodeRabbit reviews a pull request the moment it opens and again on
every push. That spends reviews on revisions that fail lint, and on pull requests
whose content was already reviewed elsewhere — release PRs being the worst case,
since they carry everything accumulated since the last release.

This workflow makes the review something a revision has to earn.

## How it works

The consuming repository turns automatic reviews off entirely:

```yaml
# .coderabbit.yml
reviews:
  auto_review:
    enabled: false
```

Nothing is reviewed on its own. This workflow then posts `@coderabbitai review`
once CI has passed — the command CodeRabbit documents as working regardless of
auto-review settings, and which it recommends itself when it skips a pull
request: *"To trigger a single review, invoke the `@coderabbitai review`
command."*

The command is the trigger. That is the whole mechanism.

### Why a command and not a label

An earlier version used `auto_review.labels: ["review-ready"]` and had the gate
apply that label. It worked, but the review then depended on four things
agreeing — `enabled`, `base_branches`, `labels`, and the label existing in the
repository — and each one broke in turn:

| Failure | Cause |
|---|---|
| every PR red on a new repo | `gh pr edit --add-label` fails on a label the repo does not define |
| release PRs reviewed anyway | a negative label match does not veto the positive trigger |
| all of `develop` refused | `base_branches` removed on the wrong assumption that it was redundant |
| a config fix could not validate itself | `.coderabbit.yml` is read from the base branch, not the head |

The command has none of those dependencies. It does not consult labels, and a
repository adopting the gate needs one line of config.

**`review-ready` still exists**, applied next to the command as a visual marker,
best-effort: a repository that never declared it still gets its reviews. Do not
put it back into `auto_review.labels` — it would become a second trigger for the
same decision, which is exactly what produced the failures above.

### One review per revision

Repeating a label is a no-op; repeating a command spends another review. Re-runs
and concurrent runs on the same commit are both reachable, so the gate writes a
marker carrying the commit:

```
@coderabbitai review

<!-- coderabbit-gate: <head_sha> -->
```

and looks for it before commenting. That is what makes "one review per revision"
true rather than merely intended. It matters more than it sounds: CodeRabbit
plans are rate-limited, and a burst of duplicate requests degrades the allowance
for the whole organisation.


### Keeping the pull request readable

Each revision adds a request from the gate, and CodeRabbit echoes every one with
an "Action performed / Review finished" reply. A pull request revised a few times
buries its human conversation under pairs of bot comments — PR #717 reached five
requests and six echoes.

Before posting a new request, the gate folds the superseded ones away with the
GraphQL `minimizeComment` mutation: its own requests as `RESOLVED`, CodeRabbit's
echoes as `OUTDATED`. They render as *"This comment was marked as resolved"* and
collapse. Nothing is deleted — one click expands them, so the record of which
revision was requested and when survives.

**Findings are never touched, by construction.** Both queries read
`/issues/{n}/comments`, which returns issue comments only. Reviews and review
comments — where findings live — are not in that endpoint. This matters more than
it sounds: on PR #717 the review carrying CodeRabbit's *"insufficient GitHub
permissions"* warning also carries 13 actionable findings, so collapsing by review
would have hidden real work. If that warning is the annoyance, the fix is granting
the app `Pull requests: Read and write`, which removes it at the source.

Also left alone: the walkthrough summary, and the sticky CI reports
(`lint-analysis`, `pr-validation-report`, `codeql-scan`) — those are updated in
place rather than duplicated, so they never accumulate.

Tidying is non-fatal throughout: losing a review because the cleanup failed would
be a bad trade.

## Scope

Two independent dimensions, OR'd together.

| Input | Matching | Question it answers |
|-------|----------|---------------------|
| `review_base_branches` | exact names | "review anything landing here" |
| `review_head_patterns` | globs on the head branch | "review this kind of branch wherever it lands" |

The head dimension exists for code that reached no other review on its way in. A
`hotfix/*` branch goes straight to `main` without passing through `develop`, so
nothing reviewed it; a release PR into the same `main` was already reviewed on the
way into `develop`.

Setting both to an empty string disables reviews without editing any workflow —
useful as a kill switch.

### The caller's trigger bounds this

A base branch listed in `review_base_branches` but absent from the caller's
`on.pull_request.branches` never sees a workflow run, so the label never arrives.
The effective scope is the **intersection** of the two, and the inputs can only
narrow within what the trigger already admits — never widen beyond it.

Widening the scope therefore means editing two places. This is deliberate: the
trigger governs which pull requests run CI at all, which is a heavier decision
than which of them get reviewed.

## Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `pr_number` | number | — | Pull request to act on. Required. |
| `checks_passed` | boolean | `false` | Whether every required check succeeded. |
| `head_sha` | string | — | Commit the verdict covers. Required — also the idempotency key. |
| `review_base_branches` | string | `develop` | Comma-separated exact base branch names. Empty removes this dimension. |
| `review_head_patterns` | string | `hotfix/*` | Comma-separated globs matched against the head branch. Empty removes this dimension. |
| `label` | string | `review-ready` | Visual marker applied alongside the command. Cosmetic — failing to apply it never fails the job. Empty disables it. |
| `dry_run` | boolean | `false` | Log the decision without changing any label. |
| `runner_type` | string | `blacksmith-4vcpu-ubuntu-2404` | Runner label. Overridden by `vars.GENERAL_RUNNERS`. |

Whitespace around commas is tolerated: `"develop, release-candidate"` works.

`checks_passed` expects the caller's verdict over its own job graph. Pass a
`failure`/`cancelled` test rather than a `success` test — most lints are
conditional on the file types touched and are `skipped` on any given pull
request, so requiring success from all of them would never release anything.

## Permissions

The calling job must grant **both**:

```yaml
permissions:
  contents: read
  pull-requests: write
```

`contents: read` is not optional even though nothing is checked out, and even
though the `gate` job overrides permissions with `pull-requests: write` alone.
GitHub validates the **workflow-level** `permissions` block of the called
workflow against what the caller grants, not just the job's. This one declares
`contents: read` at that level, so omitting it in the caller fails the run with
`startup_failure` before any job begins, with no log to explain it.

Verified by isolating it: commit `e9a4d1d` removed only that line and the run
failed to start; restoring it fixed the run.

## Secrets

| Secret | Required | Description |
|--------|----------|-------------|
| `MANAGE_TOKEN` | no | Token with `pull-requests: write` on the target repository. Falls back to `github.token` when absent, which is enough for same-repository pull requests. |

`secrets: inherit` covers it. Passing it explicitly also works:

```yaml
    secrets:
      MANAGE_TOKEN: ${{ secrets.MANAGE_TOKEN }}
```

## Usage

Minimal setup — gates the first review, which is what most repositories want:

```yaml
jobs:
  release-coderabbit:
    name: Release CodeRabbit Review
    needs: [lint, test, validate]   # every required check
    if: always() && github.event_name == 'pull_request' && github.event.pull_request.draft != true
    permissions:
      contents: read
      pull-requests: write
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/coderabbit-gate.yml@vX.Y.Z
    with:
      pr_number: ${{ github.event.pull_request.number }}
      checks_passed: ${{ !contains(needs.*.result, 'failure') && !contains(needs.*.result, 'cancelled') }}
      review_base_branches: develop
      review_head_patterns: hotfix/*
    secrets: inherit
```

`always()` is required, otherwise a skipped dependency keeps the job from running
at all and the verdict never gets evaluated.

Pin to a released version in production. When testing a change to the gate itself,
point at the branch instead — `@develop`, or `@feat/<branch>`.

## Escape hatches

The gate governs automatic reviews only. These still work on any pull request:

- commenting `@coderabbitai review`
- adding the trigger label by hand

Both are intentional. The gate is a spending policy, not an access control.

## Adoption in another repository

The gate is on by default in `go-pr-validation.yml` and `js-pr-validation.yml`, and
**inert until the repository opts in**. Three steps:

1. *(Optional)* Declare the label in `.github/labels.yml` and run the labels sync, if you want the visual marker:

   ```yaml
   - name: review-ready
     color: "0e8a16"
     description: Required checks passed — CodeRabbit is cleared to review
   ```

2. Turn automatic reviews off in `.coderabbit.yml`:

   ```yaml
   reviews:
     auto_review:
       enabled: false
   ```

   Do not add `labels:` — the command is the trigger, and a label there would
   compete with it.

3. Nothing else — the umbrella already calls the gate.

Step 1 is genuinely optional now: without the label the reviews still happen,
the pull requests just carry no badge. Only step 2 is required.

Step 2 matters as much as step 1. With the label present but `enabled` still
`true`, CodeRabbit reviews everything as before and the label decides nothing —
the gate looks installed while doing nothing.

Repositories calling **both** umbrellas should enable the gate on exactly one of
them, the same way `run_metadata` is owned by one. Two callers would each try to
release the same label, and whichever finished first would authorise before the
other had validated anything.

## What the gate does not cover

**The summary and walkthrough are not gated.** CodeRabbit regenerates them on
every push even under `auto_review.enabled: false`. On PR #708 the summary
comment's `updated_at` matched the push second for second while the pull request
carried no label and received no review. If that processing is unwanted, turn it
off separately:

```yaml
reviews:
  high_level_summary: false
  high_level_summary_in_walkthrough: false
```

Keep `review_status: true` — that is what posts *"Review skipped — required
labels: review-ready"*, the cheapest confirmation that the gate is working.

**An engaged pull request stays engaged.** Once CodeRabbit has reviewed a pull
request, incremental reviews continue on later pushes on their own — the gate
controls when a review is *requested*, not an engagement already established.
Stopping that needs `@coderabbitai ignore` in the description, or
`@coderabbitai pause` as a comment.

**Reviews are rate-limited by plan.** Requesting one is not free even when the
gate is behaving: an organisation that burns through its allowance is throttled
(observed: 61 review attempts in 7 days dropping the allowance to one review per
hour, plus the spending cap being reached). This is the reason the gate exists,
and the reason the idempotency marker matters.
