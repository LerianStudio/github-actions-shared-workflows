# Go Unit Tests Workflow

A reusable GitHub Actions workflow for running Go unit tests with support for multiple versions, platforms, and advanced testing features.

## Features

- Run tests across multiple Go versions
- Cross-platform testing (Linux, macOS, Windows)
- Race condition detection
- Coverage generation
- Parallel test execution
- Configurable timeouts
- Test result summaries
- Fast execution with caching

## Usage

### Basic Usage

```yaml
name: Unit Tests

on:
  pull_request:
    branches: [develop, release-candidate, main]
  push:
    branches: [develop, release-candidate, main]

jobs:
  unit-tests:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-unit-tests.yml@main
```

### Advanced Usage

```yaml
name: Unit Tests

on:
  pull_request:
    branches: [develop, release-candidate, main]

jobs:
  unit-tests:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-unit-tests.yml@main
    with:
      go_versions: '["1.21", "1.22", "1.23"]'
      operating_systems: '["ubuntu-latest", "macos-latest"]'
      enable_matrix: true
      enable_race_detector: true
      enable_coverage: true
      test_timeout: '15m'
      fail_fast: false
```

## Inputs

### Required

None. All inputs have sensible defaults.

### Optional

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `go_versions` | string | `["1.21", "1.22", "1.23"]` | JSON array of Go versions |
| `operating_systems` | string | `["ubuntu-latest"]` | JSON array of OS to test on |
| `runner_type` | string | `ubuntu-latest` | Runner for single-platform runs |
| `test_cmd` | string | `go test -v -short ./...` | Test command to execute |
| `enable_race_detector` | boolean | `true` | Enable race detector (-race) |
| `enable_coverage` | boolean | `false` | Generate coverage reports |
| `test_timeout` | string | `10m` | Test timeout duration |
| `enable_matrix` | boolean | `false` | Run across multiple Go/OS versions |
| `enable_test_summary` | boolean | `true` | Generate test summary |
| `fail_fast` | boolean | `false` | Stop on first failure in matrix |
| `parallel_count` | number | `0` | Parallel test count (0=default) |
| `test_flags` | string | `''` | Additional go test flags |
| `include_integration_tests` | boolean | `false` | Include integration tests |

## Outputs

This workflow does not produce outputs but creates:

- Test results in GitHub Step Summary
- Coverage reports as artifacts (if enabled)
- Test execution logs

## Permissions Required

```yaml
permissions:
  contents: read      # Required to checkout code
  checks: write       # Required for test reporting
  pull-requests: write # Required for PR comments
```

## Examples

### Single Platform, Single Go Version (Fast)

```yaml
jobs:
  unit-tests:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-unit-tests.yml@main
    with:
      enable_matrix: false
      enable_race_detector: true
```

### Multi-Version Testing

```yaml
jobs:
  unit-tests:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-unit-tests.yml@main
    with:
      go_versions: '["1.21", "1.22", "1.23"]'
      enable_matrix: true
```

### Cross-Platform Testing

```yaml
jobs:
  unit-tests:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-unit-tests.yml@main
    with:
      go_versions: '["1.23"]'
      operating_systems: '["ubuntu-latest", "macos-latest", "windows-latest"]'
      enable_matrix: true
```

### With Coverage Generation

```yaml
jobs:
  unit-tests:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-unit-tests.yml@main
    with:
      enable_coverage: true
      enable_race_detector: true
```

### Include Integration Tests

```yaml
jobs:
  unit-tests:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-unit-tests.yml@main
    with:
      include_integration_tests: true
      test_timeout: '30m'
```

### Custom Test Command

```yaml
jobs:
  unit-tests:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-unit-tests.yml@main
    with:
      test_cmd: 'go test -v -short -tags=unit ./...'
      test_flags: '-count=1'
```

### High Parallelism

```yaml
jobs:
  unit-tests:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-unit-tests.yml@main
    with:
      parallel_count: 8
      test_timeout: '5m'
```

### Fail Fast Strategy

```yaml
jobs:
  unit-tests:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-unit-tests.yml@main
    with:
      go_versions: '["1.21", "1.22", "1.23"]'
      enable_matrix: true
      fail_fast: true
```

## Test Command Flags

The workflow automatically builds test commands with:

- `-v` - Verbose output
- `-short` - Skip long-running tests (unless `include_integration_tests: true`)
- `-race` - Race detector (if `enable_race_detector: true`)
- `-coverprofile` - Coverage file (if `enable_coverage: true`)
- `-covermode=atomic` - Atomic coverage mode (with coverage)
- `-timeout` - Test timeout (from `test_timeout`)
- `-parallel` - Parallel count (if `parallel_count > 0`)

## Matrix vs Single Mode

### Single Mode (Default)
- Faster execution
- Single Go version (first in array)
- Single platform
- Best for: PR validation, quick feedback

### Matrix Mode
- Tests across multiple Go versions and platforms
- Parallel execution
- Comprehensive validation
- Best for: Main branch, release validation

## Artifacts

When `enable_coverage: true`, artifacts include:

- `coverage.txt` - Coverage data
- Retained for 7 days
- Named `coverage-$version-$os` in matrix mode

## Best Practices

### 1. PR Validation (Fast)

```yaml
on:
  pull_request:

jobs:
  unit-tests:
    uses: ./.github/workflows/go-unit-tests.yml@main
    with:
      enable_matrix: false
      enable_race_detector: true
```

### 2. Main Branch (Comprehensive)

```yaml
on:
  push:
    branches: [main]

jobs:
  unit-tests:
    uses: ./.github/workflows/go-unit-tests.yml@main
    with:
      go_versions: '["1.21", "1.22", "1.23"]'
      enable_matrix: true
      enable_coverage: true
```

### 3. Separate Unit and Integration Tests

```yaml
jobs:
  unit-tests:
    uses: ./.github/workflows/go-unit-tests.yml@main
    with:
      test_cmd: 'go test -v -short ./...'

  integration-tests:
    needs: unit-tests
    uses: ./.github/workflows/go-unit-tests.yml@main
    with:
      include_integration_tests: true
      test_timeout: '30m'
```

### 4. Skip Integration Tests in PRs

Use Go test tags:

```go
// +build integration

func TestIntegration(t *testing.T) {
    // This test only runs when -tags=integration is set
}
```

```yaml
jobs:
  unit-tests:
    uses: ./.github/workflows/go-unit-tests.yml@main
    with:
      test_cmd: 'go test -v -short -tags=!integration ./...'
```

## Race Detector

The `-race` flag detects race conditions:

- Enabled by default
- Increases memory usage
- Slows down tests by ~10x
- Critical for concurrent code

Disable for faster tests:
```yaml
with:
  enable_race_detector: false
```

## Test Timeouts

Default timeout: `10m`

Adjust based on test suite:
- Unit tests: `5m-10m`
- Integration tests: `15m-30m`
- E2E tests: `30m-1h`

```yaml
with:
  test_timeout: '15m'
```

## Parallel Execution

Go automatically parallelizes tests. Control with:

```yaml
with:
  parallel_count: 4  # Run 4 tests in parallel
```

Use `0` for Go's default (usually `GOMAXPROCS`).

## Integration with Other Workflows

### Complete CI Pipeline

```yaml
name: CI

on:
  pull_request:
    branches: [develop, release-candidate, main]

jobs:
  unit-tests:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-unit-tests.yml@main

  coverage:
    needs: unit-tests
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-coverage-check.yml@main
    with:
      coverage_threshold: 80

  lint:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-ci.yml@main
```

## Troubleshooting

### Tests Timeout

Increase timeout:
```yaml
with:
  test_timeout: '20m'
```

### Race Detector Memory Issues

Disable race detector for memory-constrained environments:
```yaml
with:
  enable_race_detector: false
```

### Tests Fail on Specific Platform

Run platform-specific tests:
```yaml
with:
  operating_systems: '["ubuntu-latest"]'
  enable_matrix: true
```

### Flaky Tests

Use `-count` flag to run tests multiple times:
```yaml
with:
  test_flags: '-count=3'
```

## Performance Tips

1. **Use `-short` flag** - Skip slow tests in unit test runs
2. **Enable caching** - Automatically enabled via `setup-go`
3. **Parallel execution** - Set `parallel_count` for large test suites
4. **Single platform first** - Use matrix only when needed
5. **Fail fast** - Enable `fail_fast: true` to save resources

## Related Workflows

- [Go Coverage Check](./go-coverage-check-workflow.md) - Coverage validation
- [Go CI](./go-ci-workflow.md) - Complete CI pipeline
- [Go Security](./go-security-workflow.md) - Security scanning

## Version History

- v1.0.0 (2025-11-24) - Initial release
  - Multi-version testing
  - Cross-platform support
  - Race detection
  - Coverage generation
  - Configurable test execution
