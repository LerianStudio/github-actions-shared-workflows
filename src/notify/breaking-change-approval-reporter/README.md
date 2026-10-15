<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>Breaking Change Approval Reporter</h1></td>
  </tr>
</table>

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
