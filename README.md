# GitHub Actions Shared Workflows

Centralized repository for reusable GitHub Actions workflows used across the Lerian organization. Simplifies CI/CD management, promotes consistency, and reduces duplication by sharing standardized pipeline configurations.

## Available Workflows

### API Dog E2E Tests

Automated API testing workflow using Apidog CLI that runs test scenarios and generates comprehensive reports. Supports both manual environment specification and automatic environment detection based on git tags (beta/rc).

**Usage (Manual Environment):**

```yaml
name: API Testing
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  api-tests:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/api-dog-e2e-tests.yml@main
    with:
      environment_id: "4770599"
      test_iterations: "1"
      output_formats: "html,cli"
      node_version: "20"
      runner_type: "ubuntu-latest"
    secrets:
      test_scenario_id: ${{ secrets.APIDOG_TEST_SCENARIO_ID }}
      apidog_access_token: ${{ secrets.APIDOG_ACCESS_TOKEN }}
```

**Usage (Auto-detect Environment from Tag):**

```yaml
name: API Testing on Release
on:
  push:
    tags:
      - '*-beta.*'
      - '*-rc.*'

jobs:
  api-tests:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/api-dog-e2e-tests.yml@main
    with:
      auto_detect_environment: true
    secrets:
      test_scenario_id: ${{ secrets.MIDAZ_APIDOG_TEST_SCENARIO_ID }}
      apidog_access_token: ${{ secrets.APIDOG_ACCESS_TOKEN }}
      dev_environment_id: ${{ secrets.MIDAZ_APIDOG_DEV_ENVIRONMENT_ID }}
      stg_environment_id: ${{ secrets.MIDAZ_APIDOG_STG_ENVIRONMENT_ID }}
```

**Inputs:**

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `environment_id` | Apidog environment ID (ignored if auto_detect_environment is true) | No | - |
| `auto_detect_environment` | Enable automatic environment detection from tag (beta/rc) | No | `false` |
| `test_iterations` | Number of test iterations | No | `"1"` |
| `output_formats` | Report formats (comma-separated) | No | `"html,cli"` |
| `node_version` | Node.js version to use | No | `"20"` |
| `runner_type` | GitHub runner type | No | `"firmino-lxc-runners"` |

**Secrets:**

| Secret | Description | Required |
|--------|-------------|----------|
| `test_scenario_id` | Apidog test scenario ID | Yes | 
| `apidog_access_token` | Apidog access token for authentication | Yes |
| `dev_environment_id` | Apidog dev environment ID (for beta tags) | No* |
| `stg_environment_id` | Apidog staging environment ID (for rc tags) | No* |

*Required when `auto_detect_environment` is `true`

**Features:**

- ✅ Automated API test execution with Apidog CLI
- ✅ Multiple output formats (HTML, CLI)
- ✅ Configurable test iterations
- ✅ Artifact upload with 30-day retention
- ✅ Test results summary in GitHub Actions
- ✅ Support for both GitHub-hosted and self-hosted runners
- ✅ Automatic environment detection from git tags (beta/rc)
- ✅ Automatic CLI cleanup after test execution

### PR Security Scan

Reusable workflow that detects changed application components in a PR and runs Trivy scans:
- Secret scan on the repository filesystem
- Vulnerability scan on built Docker images (SARIF + table outputs)

Workflow file: `.github/workflows/pr-security-scan.yml`

**Usage:**

```yaml
name: PR Security Scan
on:
  pull_request:
    branches: [ main, develop ]

jobs:
  pr-security-scan:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-security-scan.yml@main
    with:
      runner_type: ubuntu-latest
      filter_paths: |-
        components/onboarding
        components/transaction
        components/console
      path_level: "2"
      dockerhub_org: lerianstudio
```

**Inputs:**

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `runner_type` | GitHub runner type to use | No | `"ubuntu-latest"` |
| `filter_paths` | Newline-separated list of directories to monitor for changes | No | `components/onboarding`, `components/transaction`, `components/console` |
| `path_level` | Directory depth level to extract app name from path | No | `"2"` |
| `dockerhub_org` | DockerHub organization to build/tag images under | No | `"lerianstudio"` |

**Required permissions:**

```yaml
permissions:
  id-token: write       # for OIDC auth
  contents: read        # to checkout
  pull-requests: write  # to comment on PRs (if needed later)
  security-events: write # to upload SARIF to GitHub Security tab
```

**What it does:**

- Detects changed paths using `LerianStudio/github-actions-changed-paths@main` and builds a matrix of affected apps
- Runs Trivy Secret Scan (filesystem) to detect credentials and sensitive data
- Builds Docker images for each changed app and runs Trivy Vulnerability scan
- Uploads SARIF results to GitHub Security tab and prints a readable table summary
- Skips the scan if no relevant paths changed

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
