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
| `acknowledgement` | A breaking change was found on a branch outside the approval scope — no decision is needed, only the author's acknowledgement, with the exact line to paste |
| `approved` | Approved by whom, and that the next release will be a major version |
| `rejected` | Rejected by whom, the reason they gave, and what to do next |
| `unresolved` | The approval ended without a recorded decision — open the run |

Any other value fails the step. A typo in `state` must not produce a confidently
worded comment about the wrong thing.

## The button is a badge, and the alt text is the fallback

Markdown has no button, so the call to action is a [shields.io](https://shields.io)
badge wrapped in the link. That is a third party in the path of a release
control, which is worth stating plainly — so the alt text carries the entire
call to action:

```markdown
[![Review the pending deployment](https://img.shields.io/badge/...)](run-url)
```

A reader whose network blocks the image, or a day when shields is down, sees a
described link rather than a broken rectangle. Setting `badge-url` to empty
falls back to a plain `### ➡️ [Review the pending deployment](…)` heading, with
no external dependency at all.

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

**The undo example uses this pull request's own commits.** It shows the real
subjects in a `diff` block instead of a made-up `feat(scope)!: subject`. Pass
`subjects` and it uses that set — the caller that ran `breaking-change-commits`
to build the fingerprint already has it, and reading the commits a second time
costs an API call and lets this comment disagree with the set the gate judged.
Leave it empty and the composite reads them itself, so a standalone caller
needs no resolver. Only the `!` form is matched either way, because that is the
form the example illustrates — it is a view, never a verdict. The canonical
rule lives in
[`breaking-change-guard`](../../validate/breaking-change-guard/README.md); when
the two disagree the detector wins and this falls back to generic wording.

**`actual-reviewers` wins over `reviewers`.** An Environment that already existed
may be gated by different people than the caller configured, and naming the wrong
ones is worse than naming none — with neither available, the line is omitted
rather than guessed.

## Two labels, because they expire at different times

`breaking-change` is a **fact about the commits**. Approving does not make the
break go away, and somebody filtering for that label three months from now wants
this pull request in the results. It is applied in every state this composite
handles, and only the caller removes it — at the one moment the fact stops being
true, when the breaking commits are gone.

`awaiting-breaking-approval` is a **state**. It goes on while a decision is
pending and comes off the moment one is made, either way.

Collapsing the two is tempting and wrong: removing `breaking-change` on approval
erases the record exactly when it starts to matter, because now the break is
both real and agreed.

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
| `author-acknowledgement` | The exact line the author must add when it is missing. | No | `''` |
| `subjects` | Breaking commit subjects, newline-separated, as resolved by `breaking-change-commits`. Empty and the composite reads them itself. | No | `''` |
| `fingerprint` | Digest of the breaking-change commit set. Recorded when the state is `approved`, with the run that carried the approval. | No | `''` |
| `run-id` | Run recorded alongside the fingerprint, so a later run can verify the approval against the Environment log. | No | `${{ github.run_id }}` |
| `run-url` | Link to the run carrying the pending deployment. | No | `''` |
| `reviewers` | Who can answer, as a `team:<slug>` / `user:<login>` list. | No | `''` |
| `actual-reviewers` | Reviewers read from the Environment itself. Preferred over `reviewers` when present. | No | `''` |
| `server-url` | Base URL used to build commit links. | No | `${{ github.server_url }}` |
| `badge-url` | Image used as the call-to-action button. Empty falls back to a plain heading link. | No | `https://img.shields.io/badge/%E2%9E%A1%EF%B8%8F%20Review%20pending%20deployment-1f6feb?style=for-the-badge` |
| `docs-url` | Link to the explanation of how the gate works. | No | `https://github.com/LerianStudio/github-actions-shared-workflows/blob/main/docs/breaking-change-approval.md` |
| `approvers` | Comma-separated logins that approved. | No | `''` |
| `rejecters` | Comma-separated logins that rejected. | No | `''` |
| `rejection-comment` | Comment left with the rejection. | No | `''` |
| `close-on-rejection` | Whether the caller closes on rejection. Wording only. | No | `true` |
| `label` | States that the PR carries a breaking change. A fact — stays once applied. Cosmetic. | No | `''` |
| `pending-label` | States that the breaking change is waiting on a decision. Removed once approved or rejected. | No | `''` |
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
