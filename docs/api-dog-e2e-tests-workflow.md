# API Dog E2E Tests Workflow

Reusable workflow for automated API testing using Apidog CLI. Runs test scenarios and generates comprehensive reports with support for both manual environment specification and automatic environment detection.

## Features

- **Automated API testing**: Execute Apidog test scenarios via CLI
- **Environment detection**: Automatic detection based on git tags (beta/rc)
- **Multiple output formats**: HTML, CLI, JSON reports
- **Configurable iterations**: Run tests multiple times for reliability
- **Artifact retention**: 30-day report storage
- **Flexible runners**: Support for different GitHub runner types
- **Automatic cleanup**: CLI cleanup after test execution

## Usage

### Manual Environment

```yaml
api-tests:
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/api-dog-e2e-tests.yml@main
  with:
    test_iterations: "1"
    output_formats: "html,cli"
    node_version: "20"
    runner_type: "firmino-lxc-runners"
  secrets:
    test_scenario_id: ${{ secrets.APIDOG_TEST_SCENARIO_ID }}
    apidog_access_token: ${{ secrets.APIDOG_ACCESS_TOKEN }}
    environment_id: ${{ secrets.APIDOG_ENVIRONMENT_ID }}
```

### Auto-detect Environment from Tag

```yaml
api-tests:
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/api-dog-e2e-tests.yml@main
  with:
    auto_detect_environment: true
  secrets:
    test_scenario_id: ${{ secrets.APIDOG_TEST_SCENARIO_ID }}
    apidog_access_token: ${{ secrets.APIDOG_ACCESS_TOKEN }}
    dev_environment_id: ${{ secrets.APIDOG_DEV_ENVIRONMENT_ID }}
    stg_environment_id: ${{ secrets.APIDOG_STG_ENVIRONMENT_ID }}
```

### Complete Example with GitOps Integration

```yaml
name: Build and Test Pipeline
on:
  push:
    tags:
      - 'v*.*.*-beta.*'
      - 'v*.*.*-rc.*'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # ... build steps ...

  update_gitops:
    needs: build
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@main
    with:
      # ... gitops configuration ...

  e2e_tests:
    needs: update_gitops
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/api-dog-e2e-tests.yml@main
    with:
      auto_detect_environment: true
      test_iterations: "3"
      output_formats: "html,cli,json"
    secrets:
      test_scenario_id: ${{ secrets.APIDOG_TEST_SCENARIO_ID }}
      apidog_access_token: ${{ secrets.APIDOG_ACCESS_TOKEN }}
      dev_environment_id: ${{ secrets.APIDOG_DEV_ENVIRONMENT_ID }}
      stg_environment_id: ${{ secrets.APIDOG_STG_ENVIRONMENT_ID }}
```

## Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `node_version` | string | `20` | Node.js version to use |
| `test_iterations` | string | `1` | Number of test iterations |
| `output_formats` | string | `html,cli` | Report formats (comma-separated: html, cli, json) |
| `runner_type` | string | `firmino-lxc-runners` | GitHub runner type |
| `auto_detect_environment` | boolean | `false` | Enable automatic environment detection from tag |

## Secrets

### Required Secrets

| Secret | Description |
|--------|-------------|
| `test_scenario_id` | Apidog test scenario ID |
| `apidog_access_token` | Apidog access token for authentication |

### Optional Secrets

| Secret | Description | Required When |
|--------|-------------|---------------|
| `environment_id` | Apidog environment ID | `auto_detect_environment` is `false` |
| `dev_environment_id` | Apidog dev environment ID | `auto_detect_environment` is `true` |
| `stg_environment_id` | Apidog staging environment ID | `auto_detect_environment` is `true` |

## Environment Detection

When `auto_detect_environment` is enabled, the workflow automatically detects the environment based on git tag:

| Tag Pattern | Environment | Environment ID Used |
|-------------|-------------|---------------------|
| `*-beta.*` | dev | `dev_environment_id` |
| `*-rc.*` | stg | `stg_environment_id` |

**Note:** Tags must contain `-beta.` or `-rc.` (with dot) for detection to work.

## Output Formats

### Available Formats

- **html**: Generates HTML report with detailed test results
- **cli**: Console output with colored results
- **json**: JSON format for programmatic processing

### Example

```yaml
with:
  output_formats: "html,cli,json"
```

## Test Iterations

Run tests multiple times to ensure reliability:

```yaml
with:
  test_iterations: "3"  # Run tests 3 times
```

Useful for:
- Detecting flaky tests
- Performance consistency checks
- Load testing scenarios

## Artifacts

Test reports are automatically uploaded as artifacts with:
- **Name**: `apidog-e2e-test-reports-{TAG_TYPE}`
- **Retention**: 30 days
- **Contents**: All generated reports (HTML, JSON, etc.)

## Workflow Steps

1. **Checkout Repository**: Clone the repository
2. **Setup Node.js**: Install specified Node.js version
3. **Install Apidog CLI**: Install apidog-cli globally
4. **Determine Environment**: Auto-detect or use manual environment ID
5. **Run Tests**: Execute Apidog test scenario
6. **Upload Reports**: Save test reports as artifacts
7. **Cleanup**: Remove apidog-cli installation

## Best Practices

### 1. Use Auto-detect for CI/CD Pipelines

```yaml
with:
  auto_detect_environment: true
```

This ensures tests run against the correct environment based on the tag.

### 2. Run Multiple Iterations for Critical Tests

```yaml
with:
  test_iterations: "3"
```

Helps identify flaky tests and ensures consistency.

### 3. Generate Multiple Report Formats

```yaml
with:
  output_formats: "html,cli,json"
```

- HTML for human review
- CLI for quick feedback
- JSON for automation/metrics

### 4. Use Self-hosted Runners for Better Performance

```yaml
with:
  runner_type: "firmino-lxc-runners"
```

Faster execution and better resource control.

### 5. Chain with GitOps Updates

```yaml
jobs:
  update_gitops:
    # ... update deployment ...

  e2e_tests:
    needs: update_gitops
    uses: ./.github/workflows/api-dog-e2e-tests.yml@main
```

Ensures tests run after deployment is complete.

## Troubleshooting

### Environment Detection Failed

**Error**: `Unrecognized tag format for e2e tests`

**Solution**: Ensure your tag contains `-beta.` or `-rc.` with a dot:
- ✅ `v1.2.3-beta.1`
- ✅ `v1.2.3-rc.2`
- ❌ `v1.2.3-beta` (missing dot)
- ❌ `v1.2.3-rc` (missing dot)

### Tests Failing Intermittently

**Solution**: Increase test iterations to identify flaky tests:

```yaml
with:
  test_iterations: "5"
```

### Missing Environment ID

**Error**: Environment ID not set

**Solution**: When using `auto_detect_environment: true`, ensure both secrets are provided:

```yaml
secrets:
  dev_environment_id: ${{ secrets.APIDOG_DEV_ENVIRONMENT_ID }}
  stg_environment_id: ${{ secrets.APIDOG_STG_ENVIRONMENT_ID }}
```

### CLI Installation Issues

The workflow automatically cleans up the CLI after execution. If you encounter issues:

1. Check Node.js version compatibility
2. Verify network access to npm registry
3. Review runner permissions

## Getting Apidog Credentials

### Test Scenario ID

1. Open Apidog application
2. Navigate to your test scenario
3. Copy the scenario ID from the URL or settings

### Access Token

1. Go to Apidog Settings → API Access
2. Generate a new access token
3. Store in GitHub Secrets as `APIDOG_ACCESS_TOKEN`

### Environment IDs

1. Open Apidog application
2. Go to Environments section
3. Copy environment IDs for dev and staging
4. Store in GitHub Secrets

## Examples

### Basic E2E Test

```yaml
name: E2E Tests
on:
  push:
    branches: [main]

jobs:
  api-tests:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/api-dog-e2e-tests.yml@main
    secrets:
      test_scenario_id: ${{ secrets.APIDOG_TEST_SCENARIO_ID }}
      apidog_access_token: ${{ secrets.APIDOG_ACCESS_TOKEN }}
      environment_id: ${{ secrets.APIDOG_ENVIRONMENT_ID }}
```

### Release Pipeline with E2E

```yaml
name: Release Pipeline
on:
  push:
    tags:
      - 'v*.*.*-beta.*'
      - 'v*.*.*-rc.*'

jobs:
  build_and_deploy:
    runs-on: ubuntu-latest
    steps:
      # ... build and deploy steps ...

  e2e_tests:
    needs: build_and_deploy
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/api-dog-e2e-tests.yml@main
    with:
      auto_detect_environment: true
      test_iterations: "3"
      output_formats: "html,cli,json"
      runner_type: "firmino-lxc-runners"
    secrets:
      test_scenario_id: ${{ secrets.APIDOG_TEST_SCENARIO_ID }}
      apidog_access_token: ${{ secrets.APIDOG_ACCESS_TOKEN }}
      dev_environment_id: ${{ secrets.APIDOG_DEV_ENVIRONMENT_ID }}
      stg_environment_id: ${{ secrets.APIDOG_STG_ENVIRONMENT_ID }}
```

### Scheduled E2E Tests

```yaml
name: Scheduled E2E Tests
on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours

jobs:
  test_dev:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/api-dog-e2e-tests.yml@main
    with:
      test_iterations: "2"
    secrets:
      test_scenario_id: ${{ secrets.APIDOG_TEST_SCENARIO_ID }}
      apidog_access_token: ${{ secrets.APIDOG_ACCESS_TOKEN }}
      environment_id: ${{ secrets.APIDOG_DEV_ENVIRONMENT_ID }}

  test_stg:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/api-dog-e2e-tests.yml@main
    with:
      test_iterations: "2"
    secrets:
      test_scenario_id: ${{ secrets.APIDOG_TEST_SCENARIO_ID }}
      apidog_access_token: ${{ secrets.APIDOG_ACCESS_TOKEN }}
      environment_id: ${{ secrets.APIDOG_STG_ENVIRONMENT_ID }}
```

## Related Workflows

- [GitOps Update](gitops-update-workflow.md) - Update GitOps repository before running tests
- [PR Security Scan](pr-security-scan-workflow.md) - Security scanning for pull requests
