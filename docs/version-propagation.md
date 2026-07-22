<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>version-propagation</h1></td>
  </tr>
</table>

Self-controller that propagates a new `LerianStudio/github-actions-shared-workflows` release to every downstream repository declared in [`config/version-propagation.yml`](../config/version-propagation.yml).

## How it works

```
push to main
        ↓
self-release.yml
   ├── publish-release (calls release.yml — semantic-release publishes vX.Y.Z)
   └── propagate-version (if previous succeeded on main)
              ↓
       version-propagation.yml      ← reusable workflow, sets up GPG signing
              ↓
       src/config/version-propagation  ← composite, per-target loop
              ↓
       target repo: push to target_branch  (PR fallback on failure or major bump)
```

The propagation job is the last leg of the release pipeline. It resolves the just-published tag from `gh release list` (excluding pre-releases) and feeds it into the composite. If `release.yml` happens to skip (no release-worthy commits), the composite skips every target with `up-to-date` — safely idempotent.

Pre-releases (`v*-beta.N` produced by `develop`/`release-candidate`) are filtered out: the `propagate-version` job only runs on `main`, and the tag resolver excludes pre-releases.

## Behavior per target

| Condition | Result |
|---|---|
| Push to `target_branch` succeeds | Direct push, no PR |
| Push fails (branch protection, conflict, etc.) | PR opened against `target_branch` |
| Bump is `major` | PR opened (never direct push) |
| Auto-merge enabled for that bump level | `gh pr merge --auto --squash` on the fallback PR |
| Target already on `new_tag` | Skipped, no change |
| Older unmerged bump PR still open on the same `target_branch` | Closed once the new bump lands, with a comment noting it was superseded |

The `target_branch` default is `develop` (gitflow-friendly: the bump flows through `develop → release-candidate → main` via the normal promotion pipeline). Repos without `develop` declare `target_branch: main` in their target entry.

## Triggers

The propagation runs automatically as a follow-up job to every release published on `main`. There is currently no `workflow_dispatch` — to re-run for a specific tag, use GitHub Actions UI "Re-run jobs" on the `self-release` run that produced the tag.

## Required secrets (org-level, via `secrets: inherit`)

This workflow uses the same secrets already wired for the rest of the release pipeline:

| Secret | Purpose |
|---|---|
| `MANAGE_TOKEN` | PAT with `contents:write`, `pull-requests:write`, `workflows:write` on every target repo. Used for clone, push, and `gh pr create`. |
| `LERIAN_CI_CD_USER_GPG_KEY` | GPG private key — signs every commit pushed by the controller. |
| `LERIAN_CI_CD_USER_GPG_KEY_PASSWORD` | GPG passphrase. |
| `LERIAN_CI_CD_USER_NAME` | Committer name. |
| `LERIAN_CI_CD_USER_EMAIL` | Committer email. |

The `workflows:write` scope is **required** by GitHub for any edit inside `.github/workflows/` — without it, push and PR creation fail on the target repos.

## Adding a new target

Edit [`config/version-propagation.yml`](../config/version-propagation.yml) — repository-keyed map:

```yaml
repositories:
  LerianStudio/your-new-repo: {}     # inherits all defaults (develop, *.yml)

  LerianStudio/trunk-based-repo:
    target_branch: main

  LerianStudio/plugin-with-confidence:
    auto_merge_pr_fallback:
      patch: true
      minor: true                    # opt-in to auto-merge minors on PR fallback
      major: false

  LerianStudio/legacy-service:
    enabled: false                   # pause without removing the entry
```

Install the bot app on the new repo. No changes are required inside the target itself.

**Recommendation:** in target repos, keep the existing Dependabot ignore for `LerianStudio/*` so Dependabot does not race with this controller.

## Manual test (one-off, on a feature branch)

The reusable workflow is internal — to dry-run before releasing, call it from a temporary `self-*` entrypoint or via "Re-run with debug logging" from the Actions UI. Example throwaway entrypoint while testing on a branch:

```yaml
# .github/workflows/self-version-propagation-test.yml (DO NOT MERGE)
name: self-version-propagation-test
on: { workflow_dispatch: { inputs: { tag: { required: true }, filter: { default: "" }, dry: { type: boolean, default: true } } } }
jobs:
  call:
    uses: ./.github/workflows/version-propagation.yml
    with:
      new_tag: ${{ inputs.tag }}
      target_filter: ${{ inputs.filter }}
      dry_run: ${{ inputs.dry }}
    secrets: inherit
```

Inspect the run's `STEP SUMMARY` for the per-target table. Delete the file before merging.

## Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| `clone failed` for one target | Bot not installed on that repo | Install the App, re-run |
| All targets stuck on `apply-failed` | yq/sed mismatch with workflow content | Inspect dry-run output, refine `workflow_files` glob |
| Direct push falls back to PR every time | Branch protection on `target_branch` | Expected — this is the designed fallback |
| Skipped: `up-to-date` | Target workflows already reference `new_tag` | Expected — controller is idempotent |
| Workflow does not trigger on a release | Release marked as pre-release, or tag does not start with `v` | Confirm release is stable and tagged `vX.Y.Z` |

## Scope

This controller only rewrites `uses: LerianStudio/github-actions-shared-workflows/...@v<old>` to `@v<new>`. It does **not**:

- Edit workflow inputs, secrets, or job structure.
- Update files outside `.github/workflows/`.
- Touch repos absent from `config/version-propagation.yml`.

Cross-version migrations that require input or secret changes remain manual.
