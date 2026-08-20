<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>golangci-lint</h1></td>
  </tr>
</table>

Composite action that runs `golangci-lint` on a Go repository, branching on whether the triggering PR comes from a fork:

- **Non-fork PRs**: lints via [`reviewdog/action-golangci-lint`](https://github.com/reviewdog/action-golangci-lint), posting inline PR review annotations authenticated with a GitHub App token (a fork's `GITHUB_TOKEN` cannot mint this).
- **Fork PRs**: falls back to the plain [`golangci/golangci-lint-action`](https://github.com/golangci/golangci-lint-action), which only needs the default `GITHUB_TOKEN` and prints findings to the job log instead of PR comments.

Supports private `LerianStudio/*` Go modules via `GOPRIVATE`/`.netrc`, configured from `manage-token`.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `lerian-studio-push-bot-app-id` | GitHub App ID used to authenticate reviewdog PR annotations on non-fork PRs. Required only when the triggering PR is not a fork | No | `''` |
| `lerian-studio-push-bot-private-key` | GitHub App private key paired with `lerian-studio-push-bot-app-id`. Required only when the triggering PR is not a fork | No | `''` |
| `lerian-ci-cd-user-gpg-key` | GPG private key for signing the reviewdog bot identity. Required only when the triggering PR is not a fork | No | `''` |
| `lerian-ci-cd-user-gpg-key-password` | Passphrase for `lerian-ci-cd-user-gpg-key`. Required only when the triggering PR is not a fork | No | `''` |
| `lerian-ci-cd-user-name` | Git author/committer name used for the reviewdog GPG identity. Required only when the triggering PR is not a fork | No | `''` |
| `lerian-ci-cd-user-email` | Git author/committer email used for the reviewdog GPG identity. Required only when the triggering PR is not a fork | No | `''` |
| `go-version` | Go version to set up before linting | No | `1.23` |
| `golangci-lint-version` | golangci-lint version to run | No | `v1.64.8` |
| `reviewdog-level` | Minimum reviewdog annotation level (non-fork PRs only) | No | `error` |
| `fail-level` | Reviewdog level that fails the check (non-fork PRs only) | No | `any` |
| `reporter` | Reviewdog reporter type (non-fork PRs only) | No | `github-pr-review` |
| `filter-mode` | Reviewdog diff filter mode (non-fork PRs only) | No | `diff_context` |
| `cache` | Enable golangci-lint caching (non-fork PRs only) | No | `false` |
| `manage-token` | Token for `go mod download` access to private LerianStudio Go modules | No | `''` |

## Usage as composite step

```yaml
name: Go Lint
on:
  pull_request:
permissions:
  contents: read
  pull-requests: write
  checks: write
jobs:
  golangci-lint:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - name: Run golangci-lint
        uses: LerianStudio/github-actions-shared-workflows/src/lint/golangci-lint@v1.x.x
        with:
          lerian-studio-push-bot-app-id: ${{ secrets.LERIAN_STUDIO_MIDAZ_PUSH_BOT_APP_ID }}
          lerian-studio-push-bot-private-key: ${{ secrets.LERIAN_STUDIO_MIDAZ_PUSH_BOT_PRIVATE_KEY }}
          lerian-ci-cd-user-gpg-key: ${{ secrets.LERIAN_CI_CD_USER_GPG_KEY }}
          lerian-ci-cd-user-gpg-key-password: ${{ secrets.LERIAN_CI_CD_USER_GPG_KEY_PASSWORD }}
          lerian-ci-cd-user-name: ${{ secrets.LERIAN_CI_CD_USER_NAME }}
          lerian-ci-cd-user-email: ${{ secrets.LERIAN_CI_CD_USER_EMAIL }}
          manage-token: ${{ secrets.MANAGE_TOKEN }}
```

## Required permissions

```yaml
permissions:
  contents: read
  pull-requests: write # reviewdog PR review comments
  checks: write         # reviewdog check annotations
```
