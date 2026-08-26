<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>pr-commit-signatures</h1></td>
  </tr>
</table>

Fails the job when any commit in the pull request is unsigned or has an unverified signature.

The check reads GitHub's own signature verification result (`commit.verification.verified`) for **every** commit in the PR — not only `HEAD` — and reports all offending commits at once in the job summary and as `::error::` annotations, with the short SHA, a link to the commit, the author, and the verification reason.

Commits are fetched with `github.paginate`, so pull requests with more than 100 commits are fully evaluated. The Pull Request Commits API caps at 250 commits: when a PR declares more commits than the API returns, the check **fails closed** and asks for the PR to be split, rather than reporting a partial verdict.

No commit metadata beyond what is already visible in the repository is emitted, and the token is never printed.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `github-token` | GitHub token with pull-requests read permission | Yes | |
| `dry-run` | When true, report findings without failing the check | No | `false` |

## Outputs

| Output | Description |
|--------|-------------|
| `total-commits` | Number of commits evaluated in the pull request |
| `unverified-count` | Number of commits that are unsigned or unverified |

## Behavior

| Situation | Result |
|-----------|--------|
| Every commit verified | ✅ success |
| One or more commits unsigned/unverified | ❌ failure — all offenders listed |
| PR exceeds the 250-commit API cap | ❌ failure — verdict cannot be complete |
| `dry-run: true` | Findings reported via `::notice::`, job does not fail |

## Remediation

Reported in the job summary and reproduced here:

```bash
# 1. Make sure signing is configured (SSH or GPG key registered on GitHub)
git config --local commit.gpgsign true

# 2. Re-sign every commit of this branch on top of its base
git rebase --exec 'git commit --amend --no-edit -S' origin/main

# 3. Update the pull request
git push --force-with-lease
```

See [Managing commit signature verification](https://docs.github.com/en/authentication/managing-commit-signature-verification).

## Usage as composite step

```yaml
jobs:
  commit-signatures:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    permissions:
      contents: read
      pull-requests: read
    steps:
      - name: Validate commit signatures
        uses: LerianStudio/github-actions-shared-workflows/src/validate/pr-commit-signatures@v1.x.x
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

## Usage as reusable workflow

Called via the `pr-validation.yml` reusable workflow, where it runs as a blocking check (enabled by default):

```yaml
jobs:
  validate:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-validation.yml@v1.x.x
    with:
      require_verified_commits: true
    secrets: inherit
```

## Required permissions

```yaml
permissions:
  contents: read
  pull-requests: read
```

## Tests

```bash
python3 src/validate/pr-commit-signatures/test.py
```
