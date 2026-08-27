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

`withdraw` is not optional. Without it, the label from the previous revision stays
on the pull request while the new checks run, and CodeRabbit — whose incremental
reviews remain enabled — reviews a revision that may well be failing. It is also
what makes each green push get its own incremental review: the label leaves and
comes back, and that transition is the trigger.

Removal is unconditional and needs no scope check: giving up an authorisation is
always the safe direction.

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

`contents: read` is not optional even though nothing is checked out. A reusable
workflow cannot request more than its caller grants, and this one declares
`contents: read` at the top level — omitting it in the caller fails the run with
`startup_failure` before any job begins, with no log to explain it.

The workflow uses `secrets.MANAGE_TOKEN` when available and falls back to
`github.token`, so callers should pass `secrets: inherit`.

## Usage

```yaml
jobs:
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

  release-coderabbit:
    name: Release CodeRabbit Review
    needs: [withdraw-coderabbit, lint, test, validate]   # every required check
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

Pin to a released version in production. When testing a change to the gate
itself, point at the branch instead — `@develop`, or `@feat/<branch>`.

`always()` on the release job is required, otherwise a skipped dependency keeps
the job from running at all and the verdict never gets evaluated.

Listing `withdraw-coderabbit` in `needs` orders the two calls: the withdrawal can
never land after the re-application. It is skipped on events other than
`synchronize`, which `always()` tolerates.

## Escape hatches

The gate governs automatic reviews only. These still work on any pull request:

- commenting `@coderabbitai review`
- adding the trigger label by hand

Both are intentional. The gate is a spending policy, not an access control.

## Known limitation

A pull request already reviewed and then moved out of scope keeps receiving
incremental reviews. Once CodeRabbit has engaged with a pull request, removing the
label does not disengage it — the label governs the initial trigger, not an
engagement already established. Stopping that requires `@coderabbitai ignore` in
the pull request description, or `@coderabbitai pause` as a comment.

This only affects retargeting an already-reviewed pull request, not the common
paths.
