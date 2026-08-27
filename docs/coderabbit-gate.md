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

CodeRabbit's own configuration provides the mechanism. In the consuming
repository's `.coderabbit.yml`:

```yaml
reviews:
  auto_review:
    enabled: false
    labels:
      - "review-ready"
```

`enabled: false` inverts the default to *do not review*. Every pull request is out
of scope until the `review-ready` label appears, and a positive label match is
what triggers the review. This workflow is what applies that label.

Two consequences worth internalising:

- **Do not add exclusion rules to `.coderabbit.yml` expecting them to restrict
  anything.** A negative match such as `!skip-review` does not veto the positive
  trigger under `enabled: false`, and it is inert in the common case anyway — a
  pull request that never receives the label is already excluded by the inverted
  default. Scope belongs here, where it is deterministic.
- **`base_branches` has nothing to govern.** It filters which base branches are
  *auto*-reviewed, and there is no auto-review left. Restore it only alongside
  `enabled: true`.

## Modes

Called at two points of the caller's job graph.

| Mode | Position | Behaviour |
|------|----------|-----------|
| `withdraw` | early, no `needs`, on `synchronize` | Removes the label so the new revision must earn it again |
| `release` | last, needing every required check | Applies the label when the PR is in scope and nothing failed |

Calling `release` alone gates the **first** review: the label is granted once the
pull request goes green and never taken back. Adding `withdraw` makes every
revision re-earn it, which also gives each green push its own incremental review,
since the remove → add transition is what triggers one.

Removal is unconditional and needs no scope check: giving up an authorisation is
always the safe direction.

### `withdraw` buys a probability, not a guarantee

CodeRabbit decides whether to review **at the moment of the event** and publishes
minutes later. A withdrawal that lands after that decision cannot cancel it.

Measured on this repository:

| Pull request | Push | Withdrawal | Review | Outcome |
|---|---|---|---|---|
| #708 | — | 3 windows of 1–7 min without the label | none in any window | withdrawal won |
| #705 | 14:09:38 | 14:09:59 (**21s late**) | 14:15:23 | withdrawal lost |

So `withdraw` helps when CI reaction time exceeds CodeRabbit's (~1–2 min), which
is the common case, and fails when it does not. The cost is a label add/remove
pair on the timeline for every push.

Whether that trade is worth it depends on the repository. This one decided it is
not, and calls the gate in `release` mode only — see the rationale in
`.github/workflows/self-pr-validation.yml`. A repository with slow CI and
expensive reviews may reasonably decide the opposite.

Note that `release` never re-adds a label that is already present, so running it
on every push costs one short job and mutates nothing.

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
| `mode` | string | — | `release` or `withdraw`. Required. |
| `pr_number` | number | — | Pull request to act on. Required. |
| `checks_passed` | boolean | `false` | Whether every required check succeeded. Only read in `release` mode. |
| `review_base_branches` | string | `develop` | Comma-separated exact base branch names. Empty removes this dimension. |
| `review_head_patterns` | string | `hotfix/*` | Comma-separated globs matched against the head branch. Empty removes this dimension. |
| `label` | string | `review-ready` | Trigger label. Must match `reviews.auto_review.labels`. |
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
      mode: release
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

### Optional: gate every revision

Add a `withdraw` call ahead of the checks so each revision has to re-earn the
label. Read [the trade-off](#withdraw-buys-a-probability-not-a-guarantee) first —
it is a probability, paid for with timeline churn.

```yaml
  withdraw-coderabbit:
    name: Hold CodeRabbit Review
    # No needs: must land before the checks finish, not after them.
    if: github.event_name == 'pull_request' && github.event.action == 'synchronize'
    permissions:
      contents: read
      pull-requests: write
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/coderabbit-gate.yml@vX.Y.Z
    with:
      mode: withdraw
      pr_number: ${{ github.event.pull_request.number }}
    secrets: inherit
```

Then list it first in the release job's `needs`, so the withdrawal can never land
after the re-application. It is skipped on events other than `synchronize`, which
`always()` tolerates.

## Escape hatches

The gate governs automatic reviews only. These still work on any pull request:

- commenting `@coderabbitai review`
- adding the trigger label by hand

Both are intentional. The gate is a spending policy, not an access control.

## Adoption in another repository

The gate is on by default in `go-pr-validation.yml` and `js-pr-validation.yml`, and
**inert until the repository opts in**. Three steps:

1. Declare the label in `.github/labels.yml` and run the labels sync:

   ```yaml
   - name: review-ready
     color: "0e8a16"
     description: Required checks passed — CodeRabbit is cleared to review
   ```

2. Invert CodeRabbit's default in `.coderabbit.yml`:

   ```yaml
   reviews:
     auto_review:
       enabled: false
       labels:
         - "review-ready"
   ```

3. Nothing else — the umbrella already calls the gate.

Until step 1 is done the job emits a warning and exits successfully, leaving
CodeRabbit at its own behaviour. It does **not** fail the pull request: the GitHub
API rejects adding a label the repository does not define, and failing on that
would turn every pull request red in every repository that has not adopted yet.

Only a confirmed `404` is read as "not adopted". A permissions error, a rate limit
or a transient `5xx` fails the job instead — those are outages, and silently
treating them as an un-adopted repository would disable the gate while reporting
the wrong cause.

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

**A review already decided cannot be cancelled.** See the `withdraw` section
above: the decision is taken at the event, so nothing done afterwards stops the
publication.

**An engaged pull request stays engaged.** Once CodeRabbit has reviewed a pull
request, moving it out of scope does not disengage it — the label governs the
initial trigger, not an established engagement. Stopping that needs
`@coderabbitai ignore` in the description, or `@coderabbitai pause` as a comment.
