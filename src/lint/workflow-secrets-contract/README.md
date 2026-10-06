<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>workflow-secrets-contract</h1></td>
  </tr>
</table>

Fails the build when one workflow in this repository calls another and does not honour its declared secrets contract — either by falling back to `secrets: inherit`, or by forwarding fewer secrets than the called workflow declares.

## Why it exists

`secrets: inherit` hands the called workflow **every secret the caller repository holds** — not the subset it declares, and not the subset it uses. Forwarding is per call, so the bundle only travels further if the next call inherits too; in practice it did, at every hop. For a chain like `go-pr-validation` → `pr-security-scan`, each link inherited, so the credentials reaching the scan were everything the consuming repository owns rather than the five secrets the scan uses. That is CWE-732, and it is why the umbrellas now forward by name — which also stops the bundle at the first hop.

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

## How it reads a workflow

`check.py` parses each file with `yaml.compose()` and walks the job mappings, rather than scanning lines. Three shapes are the reason: a trailing comment after `uses:`, a `secrets:` key written *before* `uses:` (YAML mappings are unordered), and a job with no `secrets:` key at all — the quietest violation of the three, and the one a line scanner is most likely to walk straight past. `test.py` covers each of them, plus the accepted shapes, so a regression in the parser fails a test instead of silently narrowing what the lint sees.

Both documented local-call prefixes are recognised: `./.github/workflows/…` and `$/.github/workflows/…`, the latter being GitHub's recommended same-repository form on github.com (it takes no `@ref`, and is unavailable on GitHub Enterprise Server). A call this pattern fails to recognise is a call the lint skips in silence, so the match is deliberately kept independent of `workflows-dir`, which only resolves paths on disk.

Run the tests with `python3 src/lint/workflow-secrets-contract/test.py`; CI runs them on every self-PR.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `workflows-dir` | Directory holding the workflows to inspect. | No | `.github/workflows` |

## What it does not check

Whether a workflow **declares** every secret it references. Most release-side workflows (`release.yml`, `build.yml`, `gitops-update.yml`, and others) reference secrets they never declare and rely on inheritance from the repository that calls them — 74 such references across the repo today. Enforcing that would mean writing a contract for every one of them, which is a separate migration, not a lint fix.
