<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>Breaking Change Approval Reporter</h1></td>
  </tr>
</table>

> **Unreleased.** Until this ships in a release, reference it as `@develop` —
> `@v1` is the previous release and does not contain it yet.

Posts and keeps updated the single pull request comment that carries a breaking
change's approval state.

One comment per pull request, identified by `<!-- breaking-change-approval -->`
and edited in place on every run. A pull request revised ten times still has one
comment, and it ends as the record of who decided what — nothing is deleted.

## States

| `state` | What the comment says |
|---|---|
| `waiting` | A breaking change was found; here is the link to the pending deployment, and what approving or rejecting will do |
| `approved` | Approved by whom, and that the next release will be a major version |
| `rejected` | Rejected by whom, the reason they gave, and what to do next |
| `unresolved` | The approval ended without a recorded decision — open the run |

Any other value fails the step. A typo in `state` must not produce a confidently
worded comment about the wrong thing.

## It reads as information, not as a block

A breaking change is often deliberate, and a comment that opens with a siren
teaches people to scroll past it. The waiting comment states what was found,
links straight to the decision, and names who can make it:

> ### Breaking change — needs a decision
>
> [`f8d5506`](https://github.com/LerianStudio/example/commit/f8d5506) carries a
> breaking change, so merging makes the next release a **major** version. That is
> often deliberate — this just asks someone to confirm it.
>
> ### ➡️ [Approve or reject](https://github.com/LerianStudio/example/actions/runs/1)
>
> Who can:
> [@LerianStudio/g_github_devops](https://github.com/orgs/LerianStudio/teams/g_github_devops)

Everything else — the scope rule, the acknowledgement state, how to undo the
break — is one `<sub>` line at the bottom, present for whoever needs it and out
of the way of whoever does not.

**Reviewers are rendered as links, never as @mentions.** The pending deployment
already notifies exactly these people; a mention would ping the whole team a
second time for the same thing.

**`actual-reviewers` wins over `reviewers`.** An Environment that already existed
may be gated by different people than the caller configured, and naming the wrong
ones is worse than naming none — with neither available, the line is omitted
rather than guessed.

## What it does not do

It never closes, merges or approves anything. `close-on-rejection` only changes
the wording, so the comment matches what the caller will actually do. Keeping the
side effect in the caller is what makes this safe to run with
`continue-on-error`: losing the comment should not lose the verdict.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `github-token` | Token used to comment and label. Needs `pull-requests: write`. | Yes | — |
| `pr-number` | Pull request to report on. | Yes | — |
| `repository` | Repository owning it, as `owner/name`. | No | `${{ github.repository }}` |
| `state` | `waiting`, `approved`, `rejected` or `unresolved`. | Yes | — |
| `reason` | Why the pull request is gated, from `pr-gate-scope`. | No | `''` |
| `head-sha` | Head commit the report refers to. | No | `''` |
| `acknowledged` | Whether the author acknowledgement line is present. | No | `false` |
| `run-url` | Link to the run carrying the pending deployment. | No | `''` |
| `reviewers` | Who can answer, as a `team:<slug>` / `user:<login>` list. | No | `''` |
| `actual-reviewers` | Reviewers read from the Environment itself. Preferred over `reviewers` when present. | No | `''` |
| `server-url` | Base URL used to build commit links. | No | `${{ github.server_url }}` |
| `docs-url` | Link to the explanation of how the gate works. | No | `https://github.com/LerianStudio/github-actions-shared-workflows/blob/main/docs/breaking-change-approval.md` |
| `approvers` | Comma-separated logins that approved. | No | `''` |
| `rejecters` | Comma-separated logins that rejected. | No | `''` |
| `rejection-comment` | Comment left with the rejection. | No | `''` |
| `close-on-rejection` | Whether the caller closes on rejection. Wording only. | No | `true` |
| `label` | Applied while waiting, removed once resolved. Cosmetic. | No | `''` |
| `enabled` | `false` skips commenting while still managing the label. | No | `true` |

## Outputs

| Output | Description |
|--------|-------------|
| `comment-id` | The comment created or updated. Empty when commenting is disabled. |

## Usage

```yaml
- name: Request the approval
  uses: LerianStudio/github-actions-shared-workflows/src/notify/breaking-change-approval-reporter@v1
  with:
    github-token: ${{ secrets.MANAGE_TOKEN || github.token }}
    pr-number: ${{ needs.detect.outputs.pr-number }}
    state: waiting
    reason: ${{ needs.detect.outputs.reason }}
    run-url: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
    label: breaking-change
```

Used by [`breaking-change-approval.yml`](../../../docs/breaking-change-approval.md),
once to request and once to report the outcome.
