<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>pr-validation-reporter</h1></td>
  </tr>
</table>

Posts a single mergeability summary comment aggregating all PR validation check results (blocking + advisory). Updates the same comment on subsequent runs via a stable HTML marker instead of stacking new ones.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `github-token` | GitHub token with `pull-requests:write` and `issues:write` permissions | Yes | — |
| `source-branch-result` | Result of source branch validation | No | `skipped` |
| `title-result` | Result of PR title validation | No | `skipped` |
| `description-result` | Result of PR description validation | No | `skipped` |
| `size-result` | Result of PR size check | No | `skipped` |
| `label-result` | Result of auto-label step | No | `skipped` |
| `metadata-result` | Result of PR metadata check | No | `skipped` |
| `breaking-change-result` | Result of the blocking breaking change guard | No | `skipped` |
| `dry-run` | When `true`, skip posting the summary comment | No | `false` |

When `breaking-change-result` is `skipped` or omitted, the report omits the guard row and preserves existing mergeability behavior. This optional default exists only for backward compatibility with direct action consumers. The mandatory `pr-validation` integration always supplies the guard result and offers no guard opt-out. When supplied, only `success` is mergeable.

## Outputs

| Output | Description |
|--------|-------------|
| `has-breaking-change-guard` | Whether the breaking change guard result was reported, i.e. `breaking-change-result` was not `skipped` (`true`/`false`) |

## Usage as composite step

The `blocking-checks` job must define a `breaking-change-result` output normalized to `success`/`failure`/`cancelled`/`skipped`, derived from the [`breaking-change-guard`](../../validate/breaking-change-guard/README.md) step:

```yaml
jobs:
  blocking-checks:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    outputs:
      # ...other check outputs...
      breaking-change-result: ${{ steps.breaking-change-result.outputs.result }}
    steps:
      # ...other checks...
      - name: Breaking Change Guard
        id: breaking-change-guard
        uses: LerianStudio/github-actions-shared-workflows/src/validate/breaking-change-guard@v1.x.x
        with:
          base-ref: ${{ github.base_ref }}
          breaking-change-acknowledgement: 'BREAKING CHANGE APPROVED'
      - name: Resolve breaking change result
        id: breaking-change-result
        if: always()
        env:
          GUARD_OUTCOME: ${{ steps.breaking-change-guard.outcome }}
          HAS_BREAKING_CHANGES: ${{ steps.breaking-change-guard.outputs.has-breaking-changes }}
          APPROVED: ${{ steps.breaking-change-guard.outputs.approved }}
        run: |
          if [ "$GUARD_OUTCOME" != "success" ]; then
            echo "result=$GUARD_OUTCOME" >> "$GITHUB_OUTPUT"
          elif [ "$HAS_BREAKING_CHANGES" = "true" ] && [ "$APPROVED" != "true" ]; then
            echo "result=failure" >> "$GITHUB_OUTPUT"
          else
            echo "result=success" >> "$GITHUB_OUTPUT"
          fi

  pr-validation-report:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    needs: [blocking-checks, advisory-checks]
    if: always() && github.event.pull_request.draft != true
    steps:
      - name: Post PR Validation Summary
        uses: LerianStudio/github-actions-shared-workflows/src/notify/pr-validation-reporter@v1.x.x
        with:
          github-token: ${{ secrets.MANAGE_TOKEN || github.token }}
          source-branch-result: ${{ needs.blocking-checks.outputs.source-branch-result }}
          title-result: ${{ needs.blocking-checks.outputs.title-result }}
          description-result: ${{ needs.blocking-checks.outputs.description-result }}
          size-result: ${{ needs.advisory-checks.outputs.size-result }}
          label-result: ${{ needs.advisory-checks.outputs.label-result }}
          metadata-result: ${{ needs.advisory-checks.outputs.metadata-result }}
          breaking-change-result: ${{ needs.blocking-checks.outputs.breaking-change-result || 'skipped' }}
```

## Required permissions

```yaml
permissions:
  pull-requests: write
  issues: write
```

## Comment marker

The composite upserts a comment identified by:

```html
<!-- pr-validation-report -->
```
