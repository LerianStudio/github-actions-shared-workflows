<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>pr-checks-summary</h1></td>
  </tr>
</table>

Generates a summary table of all PR validation check results in the GitHub Actions job summary, grouped by tier (Blocking / Advisory).

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `source-branch-result` | Result of source branch validation | No | `skipped` |
| `title-result` | Result of PR title validation | No | `skipped` |
| `description-result` | Result of PR description check | No | `skipped` |
| `size-result` | Result of PR size check | No | `skipped` |
| `label-result` | Result of auto-label step | No | `skipped` |
| `metadata-result` | Result of PR metadata check | No | `skipped` |
| `breaking-change-result` | Result of the breaking change guard | No | `skipped` |
| `blocking-checks-result` | Runtime result of the blocking checks job | No | `skipped` |
| `dry-run` | Whether this is a dry run | No | `false` |

When `breaking-change-result` is `skipped` or omitted, the summary omits the guard row and preserves existing behavior. This optional default exists only for backward compatibility with direct action consumers. The mandatory `pr-validation` integration always supplies the guard result and offers no guard opt-out.

When `blocking-checks-result` is omitted, `skipped`, or `success`, the summary remains unchanged and omits the runtime row. Any other supplied value, including `failure`, `cancelled`, an empty value, or an unknown value, adds a blocking `Blocking Checks Runtime` row. This optional default exists only for backward compatibility with direct action consumers. The mandatory `pr-validation` integration always supplies this internal runtime result; it is not an opt-out.

## Outputs

| Output | Description |
|--------|-------------|
| `has-breaking-change-guard` | Whether the breaking change guard result was reported, i.e. `breaking-change-result` was not `skipped` (`true`/`false`) |
| `has-blocking-checks-runtime-failure` | Whether `blocking-checks-result` was supplied as a non-`success`, non-`skipped` value (`true`/`false`) |

## Usage as composite step

```yaml
jobs:
  pr-checks-summary:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    needs: [blocking-checks, advisory-checks]
    if: always()
    steps:
      - name: PR Checks Summary
        uses: LerianStudio/github-actions-shared-workflows/src/validate/pr-checks-summary@v1
        with:
          source-branch-result: ${{ needs.blocking-checks.outputs.source-branch-result || 'skipped' }}
          title-result: ${{ needs.blocking-checks.outputs.title-result || 'skipped' }}
          description-result: ${{ needs.blocking-checks.outputs.description-result || 'skipped' }}
          size-result: ${{ needs.advisory-checks.outputs.size-result || 'skipped' }}
          label-result: ${{ needs.advisory-checks.outputs.label-result || 'skipped' }}
          metadata-result: ${{ needs.advisory-checks.outputs.metadata-result || 'skipped' }}
          breaking-change-result: ${{ needs.blocking-checks.outputs.breaking-change-result }}
          blocking-checks-result: ${{ needs.blocking-checks.result }}
          dry-run: "true"
```

## Required permissions

```yaml
permissions:
  contents: read
```
