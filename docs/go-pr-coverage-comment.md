<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>go-pr-coverage-comment</h1></td>
  </tr>
</table>

Reusable workflow that posts/updates the sticky coverage comment on a pull request when [`go-pr-analysis.yml`](go-pr-analysis-workflow.md)'s own inline "Post coverage comment" step couldn't write it — which happens for **fork PRs**: `pull_request` runs triggered from a fork always get a read-only `GITHUB_TOKEN` and no custom secrets, regardless of `permissions:` anywhere in the call chain. GitHub gives no way to elevate that from inside a `pull_request`-triggered `workflow_call` chain.

This workflow never checks out the PR's code — it only downloads the `coverage-report-*` artifacts the analysis run already produced, so a fork PR's untrusted code never runs with a write-scoped token.

Before writing the comment, it checks whether `source_run_id` is still the latest analysis run for that PR and skips (no-op) if a newer one already exists — a caller's `workflow_run` events aren't guaranteed to arrive in order, so a delayed, stale run could otherwise overwrite a fresher comment.

## Wiring it up

Callers wire this to a `workflow_run` trigger in **their own repository** (`workflow_run` is not a fork-restricted event, so its `GITHUB_TOKEN` is write-scoped):

```yaml
name: Coverage Comment (fork fallback)
on:
  workflow_run:
    workflows: ["Go Analysis"] # the caller's own workflow name that runs go-pr-analysis.yml
    types: [completed]

jobs:
  comment:
    if: github.event.workflow_run.event == 'pull_request'
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-pr-coverage-comment.yml@tier-1
    with:
      source_run_id: ${{ github.event.workflow_run.id }}
      head_sha: ${{ github.event.workflow_run.head_sha }}
      coverage_threshold: 80
    secrets: inherit
```

`pr_number` is deliberately not an input here: `github.event.workflow_run.pull_requests` is documented by GitHub to be empty when the run comes from a forked repository — exactly the case this workflow exists for. `head_sha` is always populated, and the workflow resolves the PR from it server-side via the "list pull requests associated with a commit" API.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `source_run_id` | `run_id` of the workflow run (the one that ran `go-pr-analysis.yml`) that produced the `coverage-report-*` artifacts | Yes | — |
| `head_sha` | Head commit SHA of the pull request to comment on (e.g. `github.event.workflow_run.head_sha`) | Yes | — |
| `coverage_threshold` | Minimum coverage percentage required (0-100). Used only for the PASS/BELOW THRESHOLD label — must match the value passed to `go-pr-analysis.yml` for the same run | No | `80` |
| `dry_run` | Preview the resolved comment(s) without creating or updating anything | No | `false` |

## Outputs

| Output | Description |
|--------|-------------|
| `has_comments` | `'true'` when at least one coverage comment was created or updated (always `'false'` in `dry_run`) |

## Secrets

| Secret | Description | Required |
|--------|-------------|----------|
| `token` | Token used to download artifacts and post the comment. Defaults to the caller's `github.token`, which is write-scoped here because `workflow_run` is not a fork-restricted event | No |

## Required permissions

```yaml
permissions:
  actions: read       # download-artifact from the source run
  pull-requests: write # create/update the coverage comment
```
