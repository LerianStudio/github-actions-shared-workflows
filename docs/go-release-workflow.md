# Go Release Workflow

Automated release creation workflow using GoReleaser. Builds multi-platform binaries, creates GitHub releases with changelogs, and optionally publishes Docker images and updates Homebrew formulas.

## Features

- GoReleaser integration (supports both OSS and Pro)
- Multi-platform binary builds (Linux, macOS, Windows, ARM)
- GitHub release creation with changelogs
- Optional Docker multi-arch image builds
- Optional Homebrew formula updates
- Configurable test execution before release
- Release notifications
- Support for custom GoReleaser configurations

## Usage

### Basic Usage

```yaml
name: Release
on:
  push:
    tags:
      - 'v*.*.*'

jobs:
  release:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-release.yml@main
```

### With Docker Publishing

```yaml
name: Release
on:
  push:
    tags:
      - 'v*.*.*'

jobs:
  release:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-release.yml@main
    with:
      enable_docker: true
      docker_registry: 'ghcr.io'
      docker_platforms: 'linux/amd64,linux/arm64'
    secrets:
      docker_username: ${{ secrets.DOCKER_USERNAME }}
      docker_password: ${{ secrets.DOCKER_PASSWORD }}
```

### With Homebrew Formula

```yaml
name: Release
on:
  push:
    tags:
      - 'v*.*.*'

jobs:
  release:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-release.yml@main
    with:
      enable_homebrew: true
      homebrew_tap_repo: 'myorg/homebrew-tap'
    secrets:
      tap_github_token: ${{ secrets.TAP_GITHUB_TOKEN }}
```

### Full Configuration

```yaml
name: Release
on:
  push:
    tags:
      - 'v*.*.*'

jobs:
  release:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-release.yml@main
    with:
      go_version: '1.23'
      goreleaser_distribution: 'goreleaser'
      goreleaser_version: 'latest'
      run_tests_before_release: true
      enable_docker: true
      docker_registry: 'ghcr.io'
      docker_platforms: 'linux/amd64,linux/arm64,linux/arm/v7'
      enable_homebrew: true
      homebrew_tap_repo: 'myorg/homebrew-tap'
      enable_notifications: true
    secrets:
      tap_github_token: ${{ secrets.TAP_GITHUB_TOKEN }}
      docker_username: ${{ secrets.DOCKER_USERNAME }}
      docker_password: ${{ secrets.DOCKER_PASSWORD }}
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `runner_type` | GitHub runner type to use | No | `ubuntu-latest` |
| `go_version` | Go version for release builds | No | `1.23` |
| `goreleaser_distribution` | GoReleaser distribution (goreleaser or goreleaser-pro) | No | `goreleaser` |
| `goreleaser_version` | GoReleaser version | No | `latest` |
| `goreleaser_args` | Additional GoReleaser arguments | No | `release --clean` |
| `run_tests_before_release` | Run tests before release | No | `true` |
| `test_cmd` | Test command to execute | No | `go test -v ./...` |
| `enable_homebrew` | Enable Homebrew formula update | No | `false` |
| `homebrew_tap_repo` | Homebrew tap repository (owner/repo) | No | `''` |
| `enable_docker` | Enable Docker image build and push | No | `false` |
| `docker_registry` | Docker registry URL | No | `ghcr.io` |
| `docker_platforms` | Docker platforms (comma-separated) | No | `linux/amd64,linux/arm64` |
| `docker_tags` | Docker image tags configuration | No | Semver + latest |
| `enable_notifications` | Enable release notifications | No | `false` |

## Secrets

| Secret | Description | Required |
|--------|-------------|----------|
| `github_token` | GitHub token for releases | No (defaults to `GITHUB_TOKEN`) |
| `tap_github_token` | Token for Homebrew tap updates | No (required if `enable_homebrew` is true) |
| `docker_username` | Docker registry username | No (defaults to `github.actor` if using GHCR) |
| `docker_password` | Docker registry password/token | No (defaults to `GITHUB_TOKEN` if using GHCR) |
| `goreleaser_key` | GoReleaser Pro license key | No (only for goreleaser-pro) |

## Jobs

### release
Main release job that runs GoReleaser.

### homebrew (optional)
Updates Homebrew formula in tap repository.

### docker (optional)
Builds and pushes multi-architecture Docker images.

### notify (optional)
Sends release notifications.

## Example Configurations

### Minimal (GoReleaser OSS)

```yaml
jobs:
  release:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-release.yml@main
```

### With GoReleaser Pro

```yaml
jobs:
  release:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-release.yml@main
    with:
      goreleaser_distribution: 'goreleaser-pro'
    secrets:
      goreleaser_key: ${{ secrets.GORELEASER_KEY }}
```

### Skip Tests (Fast Release)

```yaml
jobs:
  release:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-release.yml@main
    with:
      run_tests_before_release: false
```

## Release Process

1. Create tag: `git tag v1.0.0 && git push --tags`
2. Workflow triggers: On tag push matching `v*.*.*`
3. Tests run: (if enabled) Verify everything works
4. GoReleaser builds: Creates binaries for all platforms
5. GitHub release: Created with changelog and downloads
6. Docker images: (if enabled) Published to registry
7. Homebrew formula: (if enabled) Updated in tap repo
8. Notification: (if enabled) Summary of release status

## Tips

1. Test GoReleaser locally: `goreleaser release --snapshot --clean`
2. Pin workflow version: Use `@v1.0.0` instead of `@main`
3. CHANGELOG: GoReleaser generates from commits and PRs
4. Draft releases: Use GoReleaser's `draft: true` for manual approval
5. Custom builds: Configure `.goreleaser.yml` for your needs

## Related Workflows

- [Go CI](./go-ci-workflow.md) - Continuous integration testing
- [Go Security](./go-security-workflow.md) - Security scanning

---

**Last Updated:** 2025-11-22
**Version:** 1.0.0
