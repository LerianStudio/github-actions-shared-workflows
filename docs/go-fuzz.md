<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>go-fuzz</h1></td>
  </tr>
</table>

Reusable workflow for running Go fuzz tests. Executes a configurable fuzz command and uploads failure artifacts for analysis.

## Inputs

| Input | Description | Required | Default |
|---|---|---|---|
| `runner_type` | GitHub runner type to use | No | `blacksmith-4vcpu-ubuntu-2404` |
| `go_version` | Go version to use | No | `1.25` |
| `fuzz_command` | Command to run fuzz tests | No | `make fuzz-ci` |
| `fuzz_artifacts_path` | Path pattern for fuzz failure artifacts | No | `tests/fuzz/**/testdata/fuzz/` |
| `artifacts_retention_days` | Number of days to retain fuzz failure artifacts | No | `7` |
| `dry_run` | Preview configuration without running fuzz tests | No | `false` |

## Usage

### Production

```yaml
name: Fuzz Tests

on:
  schedule:
    - cron: '0 0 * * 0'
  workflow_dispatch:

permissions:
  contents: read

jobs:
  fuzz:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-fuzz.yml@v1.12.0
    with:
      go_version: '1.25'
```

### Testing

```yaml
jobs:
  fuzz:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-fuzz.yml@develop
    with:
      go_version: '1.25'
      dry_run: true
```

### Custom fuzz command

```yaml
jobs:
  fuzz:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-fuzz.yml@v1.12.0
    with:
      go_version: '1.25'
      fuzz_command: 'go test -fuzz=. -fuzztime=30s ./...'
      fuzz_artifacts_path: '**/testdata/fuzz/'
```

## Permissions

```yaml
permissions:
  contents: read
```
