# Contributing to Shared Workflows

This document provides guidelines for contributing to the shared workflows repository.

## Git Flow

We follow a standard Git flow for this repository:

1. **Main Branch**: Contains stable, production-ready code.
2. **Develop Branch**: Used for integration and testing.
3. **Feature Branches**: Created from `main` for new features.
4. **Fix Branches**: Created from `main` for bug fixes.
5. **Hotfix Branches**: Created from `main` for urgent fixes.

## How to Update the Shared Workflow

### 1. Create a New Branch

Always create a new branch from `main` for your changes:

```bash
git checkout main
git pull
git checkout -b feature/your-feature-name
```

Use the appropriate prefix for your branch:
- `feature/` for new features
- `fix/` for bug fixes
- `hotfix/v*` for urgent fixes that need to be deployed immediately

### 2. Make Your Changes

Edit the workflow files as needed. Make sure to:
- Add clear comments to explain complex steps
- Follow YAML best practices
- Test your changes locally if possible

### 3. Commit Your Changes

Use [Conventional Commits](https://www.conventionalcommits.org/) format to enable automatic versioning and changelog generation:

```bash
git add .
git commit -m "feat: add support for new linting rules"
```

**Commit Message Format:**

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types and Version Impact:**

| Type | Description | Version Bump | Example |
|------|-------------|--------------|---------|
| `feat` | New feature | Minor (0.x.0) | `feat: add Docker login to GitOps workflow` |
| `fix` | Bug fix | Patch (0.0.x) | `fix: resolve yq checksum verification issue` |
| `perf` | Performance improvement | Minor (0.x.0) | `perf: optimize artifact download speed` |
| `build` | Build system changes | Minor (0.x.0) | `build: update semantic-release to v23` |
| `refactor` | Code refactoring | Minor (0.x.0) | `refactor: simplify environment detection logic` |
| `docs` | Documentation only | Patch (0.0.x) | `docs: update GitOps workflow examples` |
| `chore` | Maintenance tasks | Patch (0.0.x) | `chore: update dependencies` |
| `ci` | CI configuration | Patch (0.0.x) | `ci: add self-release workflow` |
| `test` | Adding tests | Patch (0.0.x) | `test: add unit tests for tag detection` |
| `BREAKING CHANGE` | Breaking change | Major (x.0.0) | See below |

**Breaking Changes:**

For breaking changes, add `BREAKING CHANGE:` in the commit footer:

```bash
git commit -m "feat: remove deprecated gitops_file input

BREAKING CHANGE: The gitops_file input has been removed. Use gitops_file_dev, gitops_file_stg, and gitops_file_prd instead."
```

**Scopes (Optional):**

Use scopes to specify which workflow is affected:
- `gitops`: GitOps Update workflow
- `e2e`: API Dog E2E Tests workflow
- `security`: PR Security Scan workflow
- `release`: Release workflow
- `docs`: Documentation

Example: `feat(gitops): add sandbox environment support`

### 4. Push Your Changes

```bash
git push origin feature/your-feature-name
```

### 5. Create a Pull Request to Develop

Create a Pull Request targeting the `develop` branch. In your PR description:
- Explain the purpose of the changes
- List any breaking changes
- Mention any dependencies that need to be updated

### 6. Testing on Develop

After your PR is merged to `develop`, test the changes by:
- Creating a test repository that uses the `@develop` tag
- Verifying all workflows run correctly
- Checking for any unexpected behavior

### 7. Promote to Main

Once testing is complete, create a Pull Request from `develop` to `main`.

This PR should summarize all changes and confirm that testing has been successful.

### 8. Automatic Release

After merging to `main`, the semantic-release process will automatically:
- Analyze commit messages to determine version bump
- Create a new version tag (e.g., `v1.2.3`)
- Generate CHANGELOG.md with all changes
- Create a GitHub release with release notes
- Back-merge changes to `develop` branch

**Release Branches:**

| Branch | Release Type | Version Format | Example |
|--------|-------------|----------------|---------|
| `develop` | Beta | `v1.2.3-beta.1` | Pre-release for development testing |
| `release-candidate` | RC | `v1.2.3-rc.1` | Pre-release for staging/UAT |
| `main` | Production | `v1.2.3` | Stable production release |

**Version Calculation:**

The version is calculated based on commit types since the last release:
- Any `BREAKING CHANGE` → Major version bump (1.0.0 → 2.0.0)
- Any `feat`, `perf`, `build`, `refactor` → Minor version bump (1.0.0 → 1.1.0)
- Any `fix`, `docs`, `chore`, `ci`, `test` → Patch version bump (1.0.0 → 1.0.1)

**Example Release Flow:**

1. Merge PR with `feat: add new workflow` to `develop`
   - Creates: `v1.2.0-beta.1`

2. Merge `develop` to `release-candidate` for testing
   - Creates: `v1.2.0-rc.1`

3. Merge `release-candidate` to `main` after approval
   - Creates: `v1.2.0`
   - Backmerges to `develop`

## Semantic Release Configuration

The repository uses semantic-release with the following configuration (`.releaserc.yml`):

**Plugins:**
- `@semantic-release/commit-analyzer` - Analyzes commits to determine version
- `@semantic-release/git` - Commits CHANGELOG.md back to repository
- `@semantic-release/github` - Creates GitHub releases
- `@saithodev/semantic-release-backmerge` - Backmerges main → develop
- `@semantic-release/exec` - Executes custom scripts

**Configuration Details:**
- CHANGELOG.md is automatically generated and committed
- Release notes are published to GitHub Releases
- Changes are automatically backmerged from main to develop
- All releases are GPG signed for security

## Important Notes

- **Never** commit directly to `main` or `develop`
- **Always** create a PR for your changes
- **Always** use conventional commit messages
- **Ensure** your changes are backward compatible when possible
- **Document** any breaking changes clearly in commit footer
- **Test** thoroughly before promoting to `main`
- **Review** CHANGELOG.md after releases to ensure accuracy

## Getting Help

If you have questions or need assistance, please contact the DevOps team.
