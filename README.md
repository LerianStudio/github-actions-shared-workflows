# GitHub Actions Shared Workflows

Centralized repository for reusable GitHub Actions workflows used across the Lerian organization. Simplifies CI/CD management, promotes consistency, and reduces duplication by sharing standardized pipeline configurations.

## Available Workflows

### API Dog E2E Tests

Automated API testing workflow using Apidog CLI that runs test scenarios and generates comprehensive reports.

**Usage:**

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
      test_scenario_id: "1407969"
      environment_id: "4770599"
      test_iterations: "1"
      output_formats: "html,cli"
      node_version: "20"
      runner_type: "ubuntu-latest"  # or "firmino-lxc-runners" for self-hosted
    secrets:
      apidog_access_token: ${{ secrets.APIDOG_ACCESS_TOKEN }}
```

**Inputs:**

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `test_scenario_id` | Apidog test scenario ID | ✅ | - |
| `environment_id` | Apidog environment ID | ✅ | - |
| `test_iterations` | Number of test iterations | ❌ | `"1"` |
| `output_formats` | Report formats (comma-separated) | ❌ | `"html,cli"` |
| `node_version` | Node.js version to use | ❌ | `"20"` |
| `runner_type` | GitHub runner type | ❌ | `"ubuntu-latest"` |

**Secrets:**

| Secret | Description | Required |
|--------|-------------|----------|
| `apidog_access_token` | Apidog access token for authentication | ✅ |

**Features:**

- ✅ Automated API test execution with Apidog CLI
- ✅ Multiple output formats (HTML, CLI)
- ✅ Configurable test iterations
- ✅ Artifact upload with 30-day retention
- ✅ Test results summary in GitHub Actions
- ✅ Support for both GitHub-hosted and self-hosted runners

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
