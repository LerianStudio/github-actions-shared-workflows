<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>needs-verdict</h1></td>
  </tr>
</table>

Computes one pass/fail verdict over every job in a `needs` context. The job's `needs:` list becomes the single place a required job is declared — adding one to the gate is a line there, not a line there plus a clause in an expression.

Two rules, both aimed at the traps of gating on a reusable workflow:

- **A job's own verdict output beats its result.** A reusable workflow's `result` also folds in jobs that report on the run rather than on the code — `Notify`, for one, whose failure to reach Slack says nothing about the code under review. A job that publishes `checks_passed` is believed over its result. A job that publishes nothing is judged by its result, so a pipeline that broke before its aggregating job ran still fails the verdict.
- **`skipped` passes.** Jobs in these pipelines are conditional on the changed files and on `enable_*` toggles, so requiring `success` from all of them would never be satisfied.

Pair it with `if: always()` on the calling job, so the verdict evaluates even when an upstream job failed or was skipped.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `needs` | The `toJSON(needs)` payload of the calling job | Yes | |
| `prefer-output` | Output name to read from a job that publishes one | No | `checks_passed` |
| `overrides` | Comma-separated `<job>=<output>` pairs for jobs whose verdict lives under another output name, e.g. `frontend-analysis=core_passed` | No | `` |
| `label` | Human-readable name of the gate, used in log output | No | `verdict` |

## Outputs

| Output | Description |
|--------|-------------|
| `passed` | `'true'` when every job passed, `'false'` otherwise |
| `failed-jobs` | Space-separated names of the jobs that failed the verdict; empty when it passed |

## Usage as composite step

```yaml
jobs:
  coderabbit-verdict:
    name: CodeRabbit Verdict
    needs: [metadata, changes, go-analysis, security, lib-version-gate]
    if: always()
    runs-on: blacksmith-4vcpu-ubuntu-2404
    outputs:
      passed: ${{ steps.verdict.outputs.passed }}
    steps:
      - name: Compute verdict
        id: verdict
        uses: LerianStudio/github-actions-shared-workflows/src/validate/needs-verdict@v1
        with:
          needs: ${{ toJSON(needs) }}
          label: CodeRabbit gate
```

## Usage as reusable workflow

```yaml
jobs:
  validation:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-pr-validation.yml@v1
    secrets: inherit
```

`go-pr-validation.yml` and `js-pr-validation.yml` already wire this composite behind `enable_coderabbit_gate`; a caller does not call it directly. The frontend umbrella passes `overrides: frontend-analysis=core_passed`, which keeps the end-to-end suite out of the review verdict without removing it from the merge gate.

## Required permissions

```yaml
permissions:
  contents: read
```
