<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>go-integration-guard</h1></td>
  </tr>
</table>

Fails the job when an integration suite that was configured to run did not actually run.

## The failure it catches

Go integration tests conventionally skip themselves when their backing service is unconfigured:

```go
dsn := os.Getenv("POSTGRES_TEST_URL")
if dsn == "" {
    t.Skip("POSTGRES_TEST_URL not set")
}
```

Under `go test ./...` that skip is invisible. The job is green and the check is named "Integration Tests". A missing job is honest — you can see it is not there. A green one that ran nothing is a claim. This guard turns the silence into a failure.

It is the difference between a suite that runs and a suite that is configured to run.

## How it works

For each package, one invocation of:

```
go test <args> -run <pattern> -v -count=1 <package>
```

and the package fails the guard if it:

| Condition | Meaning |
|---|---|
| exits non-zero | the integration tests failed |
| emits `--- SKIP` | matched the pattern but skipped — check the suite's required environment |
| emits no `--- PASS` | no test matched the pattern, so the pattern is wrong or the package does not belong in `packages` |

**One invocation per package, deliberately.** A merged log cannot express this: a package with no matching test emits neither line, so another package's pass would cover for it.

`-count=1` defeats the test cache, which would otherwise replay a pass recorded on a run that did have the service available.

**Pass `args-json` when the suite sits behind a build tag.** The guard builds its own invocation and does not inherit whatever flags the integration command used, so a suite guarded by `//go:build integration` is invisible to it and gets reported as "no test matched" right after the suite passed.

## Inputs

| Input | Description | Required | Default |
|---|---|---|---|
| `packages` | Space-separated packages that must each report a pass | Yes | — |
| `pattern` | Test-name pattern passed to `go test -run` | Yes | — |
| `args-json` | JSON array of extra flags for `go test`, e.g. `["-tags=integration"]`. Rejected unless it is an array of non-empty strings | No | `"[]"` |
| `working-dir` | Directory to run from | No | `"."` |

## Usage as composite step

```yaml
- name: Verify the integration suite actually ran
  uses: LerianStudio/github-actions-shared-workflows/src/test/go-integration-guard@v1
  with:
    packages: "./internal/store/ ./internal/httpapi/"
    pattern: "AgainstRealPostgres"
    args-json: '["-tags=integration"]'
    working-dir: .
```

## Usage as reusable workflow

Reached through `go-pr-analysis.yml` via the `integration_tests_config.guard` object:

```yaml
jobs:
  validate:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-pr-validation.yml@tier-1
    with:
      enable_integration_tests: true
      integration_tests_config: |
        { "guard": { "packages": "./internal/store/ ./internal/httpapi/",
                     "pattern": "AgainstRealPostgres",
                     "args": ["-tags=integration"] } }
    secrets: inherit
```

## Required permissions

None. Requires Go to be set up in the job (the workflow's `integration-tests` job already does this).
