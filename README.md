<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>GitHub Actions Shared Workflows</h1></td>
  </tr>
</table>

Centralized reusable GitHub Actions workflows and composite actions for the Lerian organization.

## How it works

```
Your repository workflow
         ↓
Reusable workflow (.github/workflows/*.yml)   ← orchestrates jobs
         ↓
Composite action  (src/<capability>/<name>/)  ← encapsulates steps
```

Workflows are called via `workflow_call` and versioned with semantic tags. Pin to a specific tag in production — never use `@main`.

All YAML files in this repository use the `.yml` extension — never `.yaml`.

## Available workflows

See the [`docs/`](docs/) directory for the full list, inputs, outputs, and usage examples for each workflow.

## Quick Start

```yaml
jobs:
  security:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-security-scan.yml@v1.2.3

  release:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/release.yml@v1.2.3

  gitops:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@v1.2.3
```

## Versioning

Releases follow [Semantic Versioning](https://semver.org/) via [semantic-release](https://github.com/semantic-release/semantic-release):

- Merges to `develop` → beta pre-release (`v1.2.3-beta.1`)
- Merges to `main` → stable release (`v1.2.3`)

## Repository Routines

This repository runs a consolidated weekly routine (`.github/workflows/self-routine.yml`) that keeps issues, pull requests, branches, labels, and workflow runs tidy. All scheduled jobs run in a single workflow run on **Mondays at 03:00 UTC**.

### Schedule

| Trigger | When | What it runs |
|---|---|---|
| `schedule` | Mondays 03:00 UTC | Branch cleanup, stale PRs, stale issues, labels sync, workflow runs cleanup |
| `pull_request: closed` | On every PR merge | Delete the merged feature branch |
| `push` to `main` (`.github/labels.yml`) | On label config change | Sync labels to the repo |
| `workflow_dispatch` | Manual | Run any single routine or all of them, with a `dry_run` toggle |

### Jobs

#### Branch cleanup (`branch_cleanup_stale`)
Deletes branches with no commits for **20 days**. Protected patterns (`main`, `master`, `develop`, `release/*`, `hotfix/*`) are never touched. A separate job (`branch_cleanup_merged`) deletes feature branches the moment a PR is merged.

#### Stale PRs (`stale_pr`)
- A PR with no activity for **20 days** receives a comment and the `stale` label.
- After **7 more days** of inactivity, it is closed with a closing comment.
- Any new activity (commit, comment, edit) removes the `stale` label and resets the clock.
- Exempt labels: `no-stale`, `security`, `work-in-progress`, `pinned`. Drafts are also exempt.

#### Stale issues (`stale_issue`)
- An issue with no activity for **30 days** receives a comment and the `stale` label.
- After **7 more days** of inactivity, it is closed.
- Exempt labels: `no-stale`, `security`, `pinned`.

#### Labels sync (`labels_sync`)
Reconciles the repository's labels against `.github/labels.yml`. Also fires immediately when that file changes on `main`.

#### Workflow runs cleanup (`workflow_runs_cleanup`)
Deletes workflow runs older than **90 days** to keep the Actions tab navigable.

### Effective windows

Because the cron runs weekly, items pass through the windows with up to one cron cycle of jitter. The 7-day close window aligns with the cron cadence so items are reliably picked up on the next run.

| Item | Threshold | Effective time to close (best / worst) |
|---|---|---|
| PR | 20 stale + 7 close | 27 / 34 days |
| Issue | 30 stale + 7 close | 37 / 44 days |
| Branch | 20 days inactivity | 20 / 27 days |

### Manual runs and dry_run

```yaml
# Actions → Self — Repository Routines → Run workflow
# Pick a routine and toggle dry_run (default: true)
routine: stale-pr | stale-issue | branch-cleanup-stale | labels-sync | workflow-runs-cleanup | all
dry_run: true | false
```

In `dry_run: true` mode no labels, comments, branches, or runs are touched — the per-item log under *"actions/stale per-item log"* shows exactly what would happen on a real run.

### Opting out

Add the `no-stale` label to any issue or PR you want to keep open indefinitely. The routine skips it on every scan.

## AI Assistant Support

Built-in guidance for AI assistants is included so they understand the architecture before making changes.

### Cursor IDE

Rules activate automatically based on the file open — no setup needed.

| File | Rule loaded |
|---|---|
| `src/**/*.yml` | Composite action conventions |
| `.github/workflows/*.yml` | Reusable workflow architecture |

### Claude Code CLI

```bash
claude
> /workflow    # reusable workflow rules
> /composite   # composite action rules
> /gha         # everything at once
```

**Example:**
```bash
claude
> /gha
> Add a helm-deploy composite under src/deploy/ and wire it into release.yml
```

Commands live in `.claude/commands/`. Rules live in `.cursor/rules/`.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) for branch strategy, commit conventions, and the PR process.

## Security

Report vulnerabilities privately — see [SECURITY.md](SECURITY.md). Do not open public issues.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
