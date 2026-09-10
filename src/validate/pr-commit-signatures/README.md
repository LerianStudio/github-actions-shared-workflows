<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>pr-commit-signatures</h1></td>
  </tr>
</table>

Fails the job when any commit in the pull request is unsigned or has an unverified signature.

The check reads GitHub's own signature verification result (`commit.verification.verified`) for **every** commit in the PR — not only `HEAD` — and reports all offending commits at once in the job summary and as `::error::` annotations, with the short SHA, a link to the commit, the author, and the verification reason.

The composite wraps `actions/github-script` (pinned by SHA) rather than shelling out to `gh`: it needs `github.paginate` over `github.rest.pulls.listCommits` to walk every page of commits, and Octokit's typed response exposes `commit.verification` directly. Because of that pagination, pull requests with more than 100 commits are fully evaluated.

### Past the 250-commit API cap

The Pull Request Commits API — REST and GraphQL alike — caps a pull request at 250 commits, so a release pull request carrying hundreds of commits can never be evaluated through it. When the pull request declares more than 250 commits, the composite resolves the range from the git DAG instead and verifies each commit by object ID:

1. A blobless, treeless fetch (`--filter=tree:0`) of `refs/pull/<n>/head` and the base branch into a scratch clone under `RUNNER_TEMP` — only commit objects, and it works for fork pull requests because the base repository always carries `refs/pull/<n>/head`. No checkout of the caller's workspace is involved.
2. `git rev-list <merge-base>..<head>` for the exact commit set, the same range GitHub itself reports.
3. GraphQL aliased `object(oid:)` lookups in batches of 50, reading `signature.isValid` per commit. The SHAs travel as `GitObjectID!` variables, never interpolated into the query.

The verdict then covers **every** commit, and `commit-source` reports `range` instead of `api`.

A range-sourced verdict is not trusted merely because it came from git. It is rejected — `evaluation-complete: false`, check fails — when the range comes back empty, when every line in it is filtered out, or when it was resolved for a head other than the one the pull request now points at (`refs/pull/<n>/head` moves with every push, so a range resolved mid-push describes a revision nobody is reviewing; the run for the new head is the one that decides). If the range cannot be resolved at all, verification falls back to the API, comes up short of the declared count and still **fails closed** rather than reporting a partial verdict.

The scratch clone's `.git` directory is removed by an `EXIT` trap, including on a failed fetch: a composite cannot register a post step, so the fetch credential would otherwise stay readable by every later step in the job. Only `shas.txt`, which lives outside `.git`, survives the step.

No commit metadata beyond what is already visible in the repository is emitted, and the token is never printed.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `github-token` | GitHub token with contents read and pull-requests read permission | Yes | |
| `dry-run` | When true, report findings without failing the check | No | `false` |

## Outputs

| Output | Description |
|--------|-------------|
| `total-commits` | Number of commits evaluated in the pull request |
| `unverified-count` | Number of commits that are unsigned or unverified |
| `has-signature-failures` | `true` when the check failed — any unverified commit, or a verdict that could not cover every commit. A truncated PR can report `unverified-count: 0` and still fail, which is why this output exists. |
| `evaluation-complete` | `true` when the verdict covered every commit in the pull request. `false` when the API came up short of the declared count, or when the resolved range was empty or belonged to a different head. |
| `commit-source` | `api` for pull requests at or below the 250-commit cap, `range` when the commits were resolved from the git DAG. |
| `findings-markdown` | Offending commits rendered as Markdown, ready to embed in a pull request comment. Empty when there is nothing to report. |

## Behavior

| Situation | Result |
|-----------|--------|
| Every commit verified | ✅ success |
| One or more commits unsigned/unverified | ❌ failure — all offenders listed |
| PR exceeds the 250-commit API cap | Commits resolved from the git DAG and verified in full |
| Commit range could not be resolved past the cap | ❌ failure — verdict cannot be complete |
| Resolved range empty, or resolved for a different head | ❌ failure — verdict cannot be trusted |
| `dry-run: true` | Findings reported via `::notice::`, job does not fail |

## Remediation

Reported in the job summary, where `<base-branch>` is already resolved to the pull request's own base branch:

```bash
# 1. Make sure signing is configured (SSH or GPG key registered on GitHub)
git config --local commit.gpgsign true

# 2. Re-sign every commit of this branch on top of its base
git rebase --exec 'git commit --amend --no-edit -S' origin/<base-branch>

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
      contents: read        # required to fetch the commit range past the 250-commit cap
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
