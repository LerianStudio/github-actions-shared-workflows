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

Use conventional commit messages to make the changelog generation automatic:

```bash
git add .
git commit -m "feat: add support for new linting rules"
```

Common prefixes:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `chore:` for maintenance tasks
- `refactor:` for code refactoring
- `test:` for adding tests
- `ci:` for CI configuration changes

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

### 8. Release

After merging to `main`, the semantic-release process will automatically:
- Create a new version tag
- Generate release notes
- Back-merge changes to `develop`

## Important Notes

- **Never** commit directly to `main` or `develop`
- **Always** create a PR for your changes
- **Ensure** your changes are backward compatible when possible
- **Document** any breaking changes clearly
- **Test** thoroughly before promoting to `main`

## Getting Help

If you have questions or need assistance, please contact the DevOps team.
