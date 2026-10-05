<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>workflow-secrets-contract</h1></td>
  </tr>
</table>

Fails the build when one workflow in this repository calls another and does not honour its declared secrets contract — either by falling back to `secrets: inherit`, or by forwarding fewer secrets than the called workflow declares.

## Why it exists

`secrets: inherit` hands the called workflow **every secret the caller repository holds**, and the called workflow passes that same bundle down to anything it calls in turn. For a chain like `go-pr-validation` → `pr-security-scan`, the credentials reaching the scan are everything the consuming repository owns, not the five secrets the scan uses. That is CWE-732, and it is why the umbrellas forward by name.

The failure mode on the other side is quieter and is the real reason this check is automated. A secret that is declared but not forwarded resolves to the **empty string** — no error, no warning. The job runs, the step that needed it takes its "credential absent" branch, and the pipeline stays green while the feature it guards does nothing. This check found exactly that in `release.yml`, which declared a Discord webhook path and never forwarded `DISCORD_WEBHOOK_URL` to `release-notification`.

## Rules

| | Rule | Rationale |
|---|---|---|
| 1 | A local call to a workflow that declares **at least one** secret must forward by name — `inherit` is rejected. | The callee stated what it needs; inheritance ignores that statement and over-grants. |
| 2 | An explicit `secrets:` mapping must cover **every** secret the callee declares. | A missing one is an empty string at runtime, not an error. |

A callee that declares **no** secrets is skipped entirely: it depends on inheritance by construction, and rejecting it would mean rewriting the release pipelines. This check polices declared contracts; it does not create them.

## Usage

```yaml
- name: Workflow Secrets Contract
  uses: LerianStudio/github-actions-shared-workflows/src/lint/workflow-secrets-contract@v1
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `workflows-dir` | Directory holding the workflows to inspect. | No | `.github/workflows` |

## What it does not check

Whether a workflow **declares** every secret it references. Most release-side workflows (`release.yml`, `build.yml`, `gitops-update.yml`, and others) reference secrets they never declare and rely on inheritance from the repository that calls them — 74 such references across the repo today. Enforcing that would mean writing a contract for every one of them, which is a separate migration, not a lint fix.
