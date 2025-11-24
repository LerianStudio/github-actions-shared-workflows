# Go Coverage Check Workflow

A reusable GitHub Actions workflow for checking Go code coverage thresholds and generating coverage reports.

## Features

- Calculate total code coverage percentage
- Enforce minimum coverage thresholds
- Generate coverage reports by package and function
- Post coverage results as PR comments
- Create HTML coverage reports
- Upload coverage artifacts
- Fail builds if coverage is below threshold

## Usage

### Basic Usage

```yaml
name: Coverage Check

on:
  pull_request:
    branches: [develop, release-candidate, main]
  push:
    branches: [develop, release-candidate, main]

jobs:
  coverage:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-coverage-check.yml@main
    with:
      coverage_threshold: 80
```

### Advanced Usage

```yaml
name: Coverage Check

on:
  pull_request:
    branches: [develop, release-candidate, main]

permissions:
  contents: read
  pull-requests: write

jobs:
  coverage:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-coverage-check.yml@main
    with:
      go_version: '1.23'
      coverage_threshold: 85
      fail_on_threshold: true
      enable_pr_comment: true
      report_format: 'both'
      test_cmd: 'go test -v -race -coverprofile=coverage.txt -covermode=atomic ./...'
    secrets:
      github_token: ${{ secrets.GITHUB_TOKEN }}
```

## Inputs

### Required

None. All inputs have sensible defaults.

### Optional

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `runner_type` | string | `ubuntu-latest` | GitHub runner type |
| `go_version` | string | `1.23` | Go version to use |
| `coverage_threshold` | number | `80` | Minimum coverage percentage (0-100) |
| `coverage_file` | string | `coverage.txt` | Coverage file path |
| `test_cmd` | string | `go test -v -race -coverprofile=coverage.txt -covermode=atomic ./...` | Test command |
| `enable_pr_comment` | boolean | `true` | Post coverage as PR comment |
| `fail_on_threshold` | boolean | `true` | Fail if coverage below threshold |
| `exclude_packages` | string | `''` | Packages to exclude (comma-separated) |
| `report_format` | string | `both` | Report format: text, html, or both |

## Secrets

### Optional

| Secret | Description |
|--------|-------------|
| `github_token` | GitHub token for posting PR comments. Defaults to `GITHUB_TOKEN` if not provided. Required for posting coverage comments on pull requests. |

## Outputs

This workflow does not produce outputs but creates:

- Coverage reports in GitHub Step Summary
- PR comments with coverage details (if enabled)
- HTML coverage reports as artifacts (if enabled)
- Coverage percentage in workflow logs

## Permissions Required

```yaml
permissions:
  contents: read          # Required to checkout code
  pull-requests: write    # Required to post PR comments
```

## Examples

### Enforce 90% Coverage

```yaml
jobs:
  coverage:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-coverage-check.yml@main
    with:
      coverage_threshold: 90
      fail_on_threshold: true
```

### Coverage Check Without Failing Build

```yaml
jobs:
  coverage:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-coverage-check.yml@main
    with:
      coverage_threshold: 80
      fail_on_threshold: false
      enable_pr_comment: true
```

### Custom Test Command

```yaml
jobs:
  coverage:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-coverage-check.yml@main
    with:
      test_cmd: 'go test -v -race -coverprofile=coverage.txt -covermode=atomic -tags=integration ./...'
      coverage_threshold: 75
```

### Generate Only HTML Reports

```yaml
jobs:
  coverage:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-coverage-check.yml@main
    with:
      report_format: 'html'
      enable_pr_comment: false
```

### Multiple Go Versions (Sequential)

```yaml
jobs:
  coverage-go-122:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-coverage-check.yml@main
    with:
      go_version: '1.22'
      coverage_threshold: 80

  coverage-go-123:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-coverage-check.yml@main
    with:
      go_version: '1.23'
      coverage_threshold: 80
```

## Coverage Report Format

### PR Comment Example

```markdown
## 📊 Code Coverage Report

**Overall Coverage**: `86.0%` ✅ PASS
**Threshold**: `80.0%`

## Coverage by Package

- **internal/config/config.go**: 86.0%
- **internal/version/version.go**: 90.9%

---
*Coverage threshold: 80% | Current: 86.0%*
```

### Step Summary Example

The workflow creates a detailed summary showing:
- Total coverage percentage
- Pass/fail status against threshold
- Coverage breakdown by function
- Full coverage report output

## Artifacts

When `report_format` is set to `html` or `both`, the workflow uploads:

- `coverage.txt` - Raw coverage data
- `coverage.html` - Interactive HTML coverage report

Artifacts are retained for 30 days.

## Best Practices

1. **Set Realistic Thresholds**
   - Start with current coverage level
   - Gradually increase threshold over time
   - 80%+ is considered excellent

2. **Use in Pull Requests**
   - Enable PR comments for visibility
   - Review coverage changes before merging
   - Prevent coverage regression

3. **Exclude Generated Code**
   - Use `exclude_packages` for mocks, generated files
   - Focus coverage on business logic

4. **Combine with Unit Tests Workflow**
   ```yaml
   jobs:
     unit-tests:
       uses: ./.github/workflows/go-unit-tests.yml@main

     coverage:
       needs: unit-tests
       uses: ./.github/workflows/go-coverage-check.yml@main
   ```

## Integration with CI/CD

### Pull Request Workflow

```yaml
name: PR Validation

on:
  pull_request:
    branches: [develop, release-candidate, main]

permissions:
  contents: read
  pull-requests: write

jobs:
  coverage:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-coverage-check.yml@main
    with:
      coverage_threshold: 80
      fail_on_threshold: true
      enable_pr_comment: true
```

### Push to Main (Reporting Only)

```yaml
name: Coverage Report

on:
  push:
    branches: [main]

jobs:
  coverage:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-coverage-check.yml@main
    with:
      coverage_threshold: 80
      fail_on_threshold: false
      enable_pr_comment: false
```

## Troubleshooting

### Coverage Below Threshold

If coverage fails:
1. Check the coverage report in Step Summary
2. Identify uncovered functions
3. Add tests for critical paths
4. Review HTML report for visual coverage map

### BC Command Not Found

The workflow requires `bc` for numeric comparisons. It's pre-installed on:
- ubuntu-latest ✓
- macos-latest ✓
- windows-latest (via Git Bash) ✓

### Coverage File Not Found

Ensure your `test_cmd` generates the coverage file:
```yaml
test_cmd: 'go test -v -coverprofile=coverage.txt -covermode=atomic ./...'
```

## Related Workflows

- [Go Unit Tests](./go-unit-tests-workflow.md) - Run unit tests
- [Go CI](./go-ci-workflow.md) - Complete CI pipeline
- [Go Security](./go-security-workflow.md) - Security scanning

## Version History

- v1.0.0 (2025-11-24) - Initial release
  - Coverage threshold enforcement
  - PR comments
  - HTML report generation
  - Package-level coverage breakdown
