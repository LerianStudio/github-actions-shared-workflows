# Frontend PR Analysis Workflow

Reusable workflow for comprehensive Frontend/Node.js PR analysis in monorepos. Handles change detection, linting, type checking, security scanning, testing, coverage checks, and build verification - all per changed app using a matrix strategy.

## Features

- **Change Detection**: Automatically detects which apps changed in the PR
- **Matrix Execution**: Runs all checks per changed app in parallel
- **ESLint**: Configurable linting with custom arguments
- **TypeScript**: Type checking with `tsc --noEmit`
- **Security Scanning**: npm audit for vulnerability detection
- **Unit Tests**: Runs tests with Jest/Vitest and coverage
- **Coverage Check**: Threshold enforcement with PR comments
- **Build Verification**: Ensures code compiles successfully
- **i18n Key Checks**: Optional FormatJS extraction-parity and locale-parity validation
- **Skip Logic**: Gracefully skips when no frontend changes detected
- **Package Manager Support**: npm, yarn, and pnpm

## Usage

### Single App Repository

```yaml
name: Frontend Analysis
on:
  pull_request:
    branches: [develop, main]

jobs:
  analysis:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/frontend-pr-analysis.yml@v1.0.0
    secrets: inherit
```

### Monorepo with Multiple Apps

```yaml
name: Frontend Analysis
on:
  pull_request:
    branches: [develop, main]

jobs:
  analysis:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/frontend-pr-analysis.yml@v1.0.0
    with:
      filter_paths: '["apps/web", "apps/console", "packages/ui"]'
    secrets: inherit
```

### Full Configuration

```yaml
name: Frontend Analysis
on:
  pull_request:
    branches: [develop, main]

jobs:
  analysis:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/frontend-pr-analysis.yml@v1.0.0
    with:
      filter_paths: '["apps/web", "apps/admin", "packages/shared"]'
      path_level: 2
      app_name_prefix: "console"
      node_version: "22"
      package_manager: "npm"
      eslint_args: "--max-warnings=0"
      audit_level: "high"
      coverage_threshold: 80
      fail_on_coverage_threshold: false
      enable_lint: true
      enable_typecheck: true
      enable_security: true
      enable_tests: true
      enable_coverage: true
      enable_build: true
    secrets: inherit
```

### Minimal (Only Tests and Lint)

```yaml
jobs:
  analysis:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/frontend-pr-analysis.yml@v1.0.0
    with:
      filter_paths: '["src"]'
      enable_typecheck: false
      enable_security: false
      enable_coverage: false
      enable_build: false
    secrets: inherit
```

### With Yarn

```yaml
jobs:
  analysis:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/frontend-pr-analysis.yml@v1.0.0
    with:
      package_manager: "yarn"
      node_version: "20"
    secrets: inherit
```

### With i18n Key Checks (FormatJS)

```yaml
jobs:
  analysis:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/frontend-pr-analysis.yml@v1.0.0
    with:
      app_name_prefix: "product-console"
      enable_i18n_check: true
      # i18n_check_script and i18n_keys_check_script default to
      # 'check:i18n' and 'check:i18n:keys' — override if your package.json
      # uses different script names.
    secrets: inherit
```

Warning-only mode during rollout (does not fail the workflow):

```yaml
with:
  enable_i18n_check: true
  i18n_check_fail_on_violation: false
```

### With pnpm

```yaml
jobs:
  analysis:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/frontend-pr-analysis.yml@v1.0.0
    with:
      package_manager: "pnpm"
      node_version: "22"
    secrets: inherit
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `runner_type` | GitHub runner type | No | `blacksmith-4vcpu-ubuntu-2404` |
| `filter_paths` | JSON array of paths to monitor for changes. If empty, treats repo as single-app. | No | `''` |
| `path_level` | Directory depth level to extract app name | No | `2` |
| `app_name_prefix` | Prefix for app names in matrix output | No | `''` |
| `node_version` | Node.js version to use | No | `22` |
| `package_manager` | Package manager (npm, yarn, pnpm) | No | `npm` |
| `eslint_args` | Additional ESLint arguments | No | `''` |
| `audit_level` | npm audit severity level (low, moderate, high, critical) | No | `high` |
| `coverage_threshold` | Minimum coverage percentage (0-100) | No | `80` |
| `fail_on_coverage_threshold` | Fail if coverage below threshold | No | `false` |
| `enable_lint` | Enable ESLint | No | `true` |
| `enable_typecheck` | Enable TypeScript type checking | No | `true` |
| `enable_security` | Enable security scanning (npm audit) | No | `true` |
| `enable_tests` | Enable unit tests | No | `true` |
| `enable_coverage` | Enable coverage check with PR comment | No | `true` |
| `enable_build` | Enable build verification | No | `true` |
| `enable_i18n_check` | Enable i18n key validation (runs both i18n scripts) | No | `false` |
| `i18n_check_script` | npm script for extraction-parity check | No | `check:i18n` |
| `i18n_keys_check_script` | npm script for locale-parity check | No | `check:i18n:keys` |
| `i18n_check_fail_on_violation` | Fail the workflow on i18n violations (set `false` for warning-only rollout) | No | `true` |

## Secrets

Uses `secrets: inherit` pattern. Required secrets:

| Secret | Description | Required When |
|--------|-------------|---------------|
| `MANAGE_TOKEN` | GitHub token for PR comments | PR comments (falls back to GITHUB_TOKEN) |
| `SLACK_WEBHOOK_URL` | Slack webhook for notifications | Optional |

## Jobs

### detect-changes
Detects which apps have changes based on `filter_paths`, delegating to the [`changed-paths`](../src/config/changed-paths/README.md) composite action. Outputs a matrix of changed apps for subsequent jobs.

### lint
Runs ESLint per changed app. Configurable arguments via `eslint_args`.

### typecheck
Runs TypeScript compiler (`tsc --noEmit`) per changed app to check for type errors.

### security
Runs npm audit per changed app:
- Checks for vulnerabilities in dependencies
- Configurable severity level via `audit_level`
- Only checks production dependencies (`--omit=dev`)

### tests
Runs unit tests per changed app with:
- Coverage profiling (json-summary, lcov, text)
- Uploads coverage artifacts
- Works with Jest, Vitest, or any test runner that supports coverage

### coverage
Calculates coverage and posts PR comment per changed app:
- Downloads coverage artifact from `tests` job
- Parses `coverage-summary.json` for metrics
- Compares against threshold
- Posts formatted coverage report as PR comment

### build
Verifies code compiles/builds successfully per changed app.

### i18n-check

Optional. Validates internationalization keys per changed app by running two npm scripts:

- `i18n_check_script` (default `check:i18n`) — extraction parity: catches keys used in source that were never extracted to locale files.
- `i18n_keys_check_script` (default `check:i18n:keys`) — locale parity: catches keys present in some locale files but missing from others.

Gated by `enable_i18n_check` (default `false`). When `i18n_check_fail_on_violation: false`, violations are reported but do not fail the workflow — useful during initial rollout in noisy codebases.

### no-changes
Runs when no frontend changes are detected - outputs skip message.

### notify
Sends Slack notification with workflow status (if webhook configured).

## How Change Detection Works

1. Compares changed files between PR base and head
2. Extracts directory paths up to `path_level` depth
3. Filters paths matching `filter_paths` array
4. Builds matrix with `name` and `working_dir` for each changed app

**Example:**

```
filter_paths: '["apps/web", "apps/admin"]'
path_level: 2

Changed files:
- apps/web/src/components/Button.tsx
- apps/web/src/hooks/useAuth.ts
- apps/admin/pages/dashboard.tsx

Resulting matrix:
[
  {"name": "web", "working_dir": "apps/web"},
  {"name": "admin", "working_dir": "apps/admin"}
]
```

With `app_name_prefix: "console"`:
```
[
  {"name": "console-web", "working_dir": "apps/web"},
  {"name": "console-admin", "working_dir": "apps/admin"}
]
```

## PR Comment Format

Coverage reports are posted as PR comments in this format:

```markdown
## 📊 Unit Test Coverage Report: `console-web`

| Metric | Value | Status |
|--------|-------|--------|
| **Lines** | `85.5%` | ✅ PASS |
| **Statements** | `84.2%` | |
| **Branches** | `78.3%` | |
| **Functions** | `90.1%` | |
| **Threshold** | `80%` | |

---
*Generated by Frontend PR Analysis workflow*
```

## Package Manager Commands

The workflow automatically adapts commands based on `package_manager`:

| Action | npm | yarn | pnpm |
|--------|-----|------|------|
| Install | `npm ci` | `yarn install --frozen-lockfile` | `pnpm install --frozen-lockfile` |
| Lint | `npx eslint .` | `yarn eslint .` | `pnpm eslint .` |
| Test | `npm test -- --coverage` | `yarn test --coverage` | `pnpm test --coverage` |
| Build | `npm run build` | `yarn build` | `pnpm build` |
| Audit | `npm audit --omit=dev` | `yarn audit` | `pnpm audit` |

## Tips

1. **Pin to version tag**: Use `@v1.0.0` instead of `@v1.0.0` for production stability
2. **Custom ESLint config**: Place `.eslintrc` or `eslint.config.js` in each app directory for app-specific rules
3. **Coverage threshold**: Start with `fail_on_coverage_threshold: false` and enable once baseline is established
4. **Test framework**: Works with Jest, Vitest, or any test runner that outputs `coverage-summary.json`
5. **Performance**: Jobs run in parallel per app - more apps = more parallelism
6. **TypeScript config**: Ensure `tsconfig.json` exists in each app directory for type checking

## Permissions Required

The workflow requires these permissions:
- `contents: read` - To checkout code
- `pull-requests: write` - To post coverage comments
- `security-events: write` - For security scanning results

## Related Workflows

- [Go PR Analysis](./go-pr-analysis-workflow.md) - Equivalent workflow for Go projects
- [Changed Paths](./changed-paths-workflow.md) - Standalone change detection
- [Build](./build-workflow.md) - Docker image builds
- [Slack Notify](./slack-notify-workflow.md) - Workflow notifications
- [PR Security Scan](./pr-security-scan-workflow.md) - Additional security scanning with Trivy

---

**Last Updated:** 2025-12-23
**Version:** 1.0.0
