<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>Environment Approvals</h1></td>
  </tr>
</table>

> **Unreleased.** Until this ships in a release, reference it as `@develop` —
> `@v1` is the previous release and does not contain it yet.

Reads who approved or rejected a workflow run's pending deployment to a given
Environment.

GitHub exposes the decision in two places: the gated job's conclusion, and the
run's approval log. The conclusion is lossy — a rejection and a cancellation can
both leave the job non-successful — so anything that acts on the decision should
read the log, which records who decided, what, and why.

## `api-readable` is not a detail

Reading the approval log needs `actions: read`. A called workflow may only
request permissions its caller already holds, so a reusable workflow often cannot
declare it, and the call comes back 403.

When that happens the lists are empty — and empty lists would otherwise be
indistinguishable from "nobody rejected". `api-readable=false` is how the caller
knows the difference and falls back to something it trusts.

A caller that ignores this output and treats empty `rejecters` as "no rejection"
has a gate that silently stops rejecting the day its token scope changes.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `github-token` | Token used to read the approvals. Needs `actions: read`. | Yes | — |
| `environment` | Environment whose decisions are collected. | Yes | — |
| `run-id` | Workflow run to read. | No | `${{ github.run_id }}` |
| `repository` | Repository owning the run, as `owner/name`. | No | `${{ github.repository }}` |

## Outputs

| Output | Description |
|--------|-------------|
| `approvers` | Comma-separated logins that approved. |
| `rejecters` | Comma-separated logins that rejected. |
| `rejection-comment` | Comment left with the most recent rejection, newlines flattened. |
| `api-readable` | Whether the API could be read at all. `false` means the lists are empty for lack of permission, **not** for lack of decisions. |

## Usage

```yaml
- name: Collect the decisions
  id: decisions
  continue-on-error: true
  uses: LerianStudio/github-actions-shared-workflows/src/validate/environment-approvals@v1
  with:
    github-token: ${{ secrets.MANAGE_TOKEN || github.token }}
    environment: breaking-approval

- name: Decide
  env:
    REJECTERS: ${{ steps.decisions.outputs.rejecters }}
    API_READABLE: ${{ steps.decisions.outputs.api-readable }}
    APPROVAL_RESULT: ${{ needs.approval.result }}
  run: |
    # Fall back to the job conclusion only when the log was unreadable.
    if [ -z "$REJECTERS" ] && [ "$API_READABLE" != "true" ] \
      && [ "$APPROVAL_RESULT" = "failure" ]; then
      REJECTERS="a reviewer"
    fi
```
