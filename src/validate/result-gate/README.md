<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>result-gate</h1></td>
  </tr>
</table>

Fails the job unless an upstream job `result` is `success` or `skipped`. Used as the final aggregation step over a multi-job reusable pipeline (called with `uses:`), so branch protection can require a single stable check name instead of the pipeline's internal job names.

Pair it with `if: always()` on the gate job so the gate evaluates even when the upstream pipeline failed.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `result` | The `needs.<job>.result` value to evaluate (`success`, `failure`, `cancelled`, `skipped`) | Yes | |
| `label` | Human-readable name of the gated pipeline, used in log output | No | `pipeline` |

## Usage as composite step

```yaml
jobs:
  go-analysis:
    uses: ./.github/workflows/go-pr-analysis.yml
    secrets: inherit

  go-analysis-gate:
    name: Go Analysis
    needs: [go-analysis]
    if: always()
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - name: Aggregate Go Analysis result
        uses: LerianStudio/github-actions-shared-workflows/src/validate/result-gate@v1
        with:
          result: ${{ needs.go-analysis.result }}
          label: Go Analysis
```

## Required permissions

```yaml
permissions:
  contents: read
```
