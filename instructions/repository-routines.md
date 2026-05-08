<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>Repository Routines — Contributor Guide</h1></td>
  </tr>
</table>

> **You probably landed here from a comment on a PR or issue.** This page explains what the automation does, why your item was flagged, and what you can do about it.

## What is "the routine"?

Every Lerian repository runs a single weekly maintenance routine that takes care of housekeeping tasks no one wants to do manually:

| Task | What it does |
|---|---|
| **Stale PR scan** | Flags PRs with no activity in 20 days, closes them 7 days later if still untouched |
| **Stale issue scan** | Flags issues with no activity in 30 days, closes them 7 days later if still untouched |
| **Branch cleanup (post-merge)** | Deletes the source branch immediately after a PR is merged |
| **Branch cleanup (stale)** | Deletes branches with no commits for 20 days and no open PR attached |
| **Labels sync** | Keeps repository labels aligned with `.github/labels.yml` |
| **Workflow runs cleanup** | Deletes Actions runs older than 45 days |

The routine runs every **Monday at 03:00 UTC**. Operators can tune the thresholds per repository — the values above are the shared defaults.

---

## Why was my PR or issue flagged as stale?

Because nothing happened on it for the inactivity window (20 days for PRs, 30 days for issues). "Activity" means: a new commit, a comment, a label change, a re-request for review, or a reopen. The bot does not look at your calendar — only at the item's event timeline.

### How to keep it open

You have several options:

1. **Just engage with it.** Push a commit, leave a comment, request a review. Any of these resets the inactivity counter and removes the `stale` label automatically.
2. **Apply the `no-stale` label.** This permanently exempts the item from the routine. Use it for things that are intentionally long-lived: tracking issues, parent epics, planned-but-not-yet-prioritized work.
3. **Apply one of the other exempt labels.** These also pause the routine:
   - `security` — security-sensitive items that shouldn't be auto-closed under any circumstances
   - `work-in-progress` (PRs only) — work explicitly paused, kept for context
   - `pinned` (issues only) — issues kept on top of the backlog by intent

If none of those fit and you want the item to close, do nothing — closure happens automatically after the second window expires.

### My item was closed but it's still relevant

Reopen it. Stale closure is a soft signal, not a verdict. When you reopen, add a comment explaining the next step (re-scoping, waiting on a dependency, etc.) and apply `no-stale` if it'll sit for a while.

---

## Why was my branch deleted?

Two cases:

**Post-merge deletion.** When a PR is merged, the head branch is deleted immediately. This is the same behavior as GitHub's "Automatically delete head branches" setting — we run it as part of the routine so it works consistently across repos. Your code is preserved in the merge commit; nothing is lost.

**Stale branch sweep.** Branches with no commits in 20+ days **and** no open PR are deleted in the weekly run. Protected branches (`main`, `master`, `develop`, `release/*`, `hotfix/*`) and any branch with GitHub branch protection rules are never touched.

If you need a long-lived working branch:

- Open a draft PR pointing to it — the open PR keeps it alive.
- Or add it to your repository's protected-branch patterns (ask the maintainers).

If a branch you needed was deleted, the commits are not gone — they're still reachable from any PR, fork, or local clone. Restore it with `git push origin <sha>:<branch-name>`.

---

## Anatomy of a stale comment

When the bot comments on your PR or issue, it tells you:

- **The window that elapsed** — e.g., "no activity for 20 days"
- **When it will be closed** — e.g., "in 7 days unless updated"
- **How to keep it open** — applying `no-stale` or activity

Reading the comment is enough to know what to do. This page exists for the broader context.

---

## For maintainers

If you operate this routine in your repository (or you're configuring it for a new one), see the operator documentation:

- [`docs/routine.md`](../docs/routine.md) — reusable workflow inputs, integration patterns, defaults
- [`docs/stale-pr.md`](../docs/stale-pr.md), [`docs/stale-issue.md`](../docs/stale-issue.md) — individual stale workflow references
- [`docs/branch-cleanup.md`](../docs/branch-cleanup.md) — branch cleanup reference
- [`docs/labels-sync.md`](../docs/labels-sync.md) — labels sync reference
- [`docs/workflow-runs-cleanup.md`](../docs/workflow-runs-cleanup.md) — workflow runs cleanup reference

The link the bot posts in stale comments is set by the `docs-url` input on the `src/config/stale` composite, defaulting to this page on `main`. To customize per repository, expose `docs_url` as a `workflow_call` input on `stale-pr.yml` / `stale-issue.yml` / `routine.yml` and forward it to the composite.

---

## Summary cheat sheet

| Want to… | Do this |
|---|---|
| Keep my PR/issue alive once | Comment, push, or re-request review |
| Keep my PR/issue alive forever | Apply the `no-stale` label |
| Keep a security item alive | Apply the `security` label |
| Pause a PR while preserving it | Apply the `work-in-progress` label |
| Keep a long-lived branch | Open a draft PR pointing to it |
| Restore a deleted branch | `git push origin <sha>:<branch>` (commits aren't lost) |
