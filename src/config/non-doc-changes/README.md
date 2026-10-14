<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>non-doc-changes</h1></td>
  </tr>
</table>

Detects whether a pull request or push contains changes beyond documentation/meta files. Use it to gate expensive pipelines (analysis, security, release) so documentation-only changes don't trigger a full run.

It auto-detects the event:

- `pull_request` / `pull_request_target` — lists changed files via `gh api repos/{repo}/pulls/{n}/files`. Deleted files are included and classified by their path, so a deletion-only pull request is gated on what it deleted rather than treated as an empty diff.
- `push` — diffs `before...after` via `gh api repos/{repo}/compare`. A first push (empty/zero base ref) returns `code=true`.

A changed file "counts" unless it matches one of the `ignore-globs` patterns. If every changed file matches an ignore pattern, `code=false`.

Files under `.github/workflows/`, `.github/actions/` and `.github/scripts/` are classified before the globs are applied, and `workflow-paths-are-code` decides how:

- `true` (the default) — they count as code whatever the globs say. The default `.github/*` glob exists for CODEOWNERS, templates and bot config, and the PR that edits only the pipeline definition is the one PR that must run the pipeline it edits. This is what the validation and CI umbrellas want.
- `false` — they are classified by the globs like any other path, so the default `.github/*` matches them and the gate returns `code=false`. This is what the release umbrellas pass: a push that edits only the pipeline ships byte-identical code, and releasing it publishes new images, moves GitOps tags and writes a changelog entry for an internal CI tweak.

An unrecognised value fails the step. A typo would not fail here, it would decide — and neither reading is safe to guess at.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `github-token` | GitHub token for gh CLI access (read on contents and pull requests) | Yes | |
| `ignore-globs` | Space-separated glob patterns treated as documentation/meta | No | `*.md docs/* .github/* LICENSE* .gitignore .coderabbit.yml .coderabbit.yaml` |
| `workflow-paths-are-code` | Classify `.github/workflows/`, `.github/actions/` and `.github/scripts/` as code before the globs are applied. Release callers pass `false` | No | `true` |

## Outputs

| Output | Description |
|--------|-------------|
| `code` | `true` when at least one changed file is not matched by `ignore-globs`; `false` otherwise |

## Usage as composite step

```yaml
jobs:
  changes:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    outputs:
      code: ${{ steps.gate.outputs.code }}
    steps:
      - name: Non-doc change gate
        id: gate
        uses: LerianStudio/github-actions-shared-workflows/src/config/non-doc-changes@v1
        with:
          github-token: ${{ github.token }}
          ignore-globs: "*.md docs/* .github/* LICENSE* .gitignore .coderabbit.yml .coderabbit.yaml"
          # Release callers add this, so a .github/**-only push does not release:
          # workflow-paths-are-code: "false"
```

## Required permissions

```yaml
permissions:
  contents: read
  pull-requests: read
```
