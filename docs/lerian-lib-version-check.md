<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>lerian-lib-version-check</h1></td>
  </tr>
</table>

Reusable workflow that enforces up-to-date LerianStudio Go libraries in every consumer service. It is intended to run on pull requests as a blocking check, alongside the standard PR analysis pipeline.

## Why

LerianStudio libraries (`lib-commons`, `lib-auth`, `lib-license-go`, …) evolve quickly. Apps that fall behind drift from organisation standards, miss bug fixes and security patches, and force reviewers to manually check dependency freshness on every PR. A Go service with **no** Lerian dependencies at all is, by definition, off-standard.

This workflow turns those expectations into a CI gate.

## Features

- **Strict latest-stable enforcement** — every direct Lerian dep must be on the latest stable GitHub release.
- **Major-bump grace window** — major-version bumps are tolerated while the latest release is younger than the grace window (default 3 days); minor and patch bumps are always enforced immediately. Configured org-wide via a GitHub variable.
- **Standards gate** — services with no Lerian libs in `go.mod` fail the check.
- **Sticky PR comment** — a single comment is created and updated in place with a status table.
- **`.lerianstudiolibignore`** — gitignore-style exemption file for temporary skips or version pins.
- **Soft missing-file behaviour** — a missing ignore file produces a warning, not a failure.
- **Dry-run mode** — verbose log of all resolved versions, never fails.
- **Pre-release skipping** — `-beta`, `-rc`, and draft releases are ignored when picking the latest stable.

## Architecture

```
lerian-lib-version-check.yml (reusable workflow)
   ↓
src/validate/lerian-lib-version (composite action)
   ↓
   1. Parse go.mod for github.com/LerianStudio/* direct deps
   2. Load .lerianstudiolibignore (if present)
   3. For each lib: GET /repos/LerianStudio/<repo>/releases (paged, stable only)
   4. Compare current vs latest using semver (sort -V)
   4b. Apply the major-bump grace window (unpinned libs only)
   5. Build markdown report, write step summary
   6. Upsert sticky PR comment (via actions/github-script)
   7. Exit non-zero if outdated or no Lerian libs detected
```

## Usage

### Basic

```yaml
name: PR Checks

on:
  pull_request:
    branches: [develop, main]
    types: [opened, synchronize, reopened, ready_for_review]

permissions:
  contents: read
  pull-requests: write

jobs:
  lerian-lib-version-check:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/lerian-lib-version-check.yml@v1.x.x
```

### Custom configuration

```yaml
jobs:
  lerian-lib-version-check:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/lerian-lib-version-check.yml@v1.x.x
    with:
      go_mod_path: services/api/go.mod
      ignore_file: .config/.lerianstudiolibignore
      check_indirect: false
      comment_on_pr: true
      dry_run: false
```

### Gating downstream jobs

```yaml
jobs:
  lerian-lib-version-check:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/lerian-lib-version-check.yml@v1.x.x

  deploy:
    needs: lerian-lib-version-check
    if: needs.lerian-lib-version-check.outputs.has_outdated == 'false'
    runs-on: ubuntu-latest
    steps:
      - run: echo "All Lerian deps are current — safe to deploy."
```

## Inputs

| Name             | Type    | Default                     | Description                                                                                  |
|------------------|---------|-----------------------------|----------------------------------------------------------------------------------------------|
| `runner_type`    | string  | `blacksmith-4vcpu-ubuntu-2404` | Runner label                                                                              |
| `go_mod_path`    | string  | `go.mod`                    | Path to `go.mod` relative to the repo root                                                   |
| `ignore_file`    | string  | `.lerianstudiolibignore`    | Path to the optional ignore file. Missing file produces a warning, not a failure.            |
| `check_indirect` | boolean | `false`                     | Also check transitive (`// indirect`) deps                                                   |
| `comment_on_pr`  | boolean | `true`                      | Post / update a sticky comment on the PR with the result table                               |
| `major_bump_grace_days` | string | `''`                | Per-invocation override for the major-bump grace window. Takes precedence over the `LERIAN_LIB_MAJOR_BUMP_GRACE_DAYS` variable; empty uses the variable, then defaults to `3`. |
| `dry_run`        | boolean | `false`                     | Verbose log of all resolved versions; never fails the build                                  |

## Major-bump grace window

Major-version bumps (a higher major on an unpinned, API-resolved lib) are tolerated while the latest release is younger than the grace window. Minor and patch bumps are always enforced immediately. This gives teams a short buffer to plan the import-path migration a major bump requires, without letting it linger.

The window is resolved in this order: the per-invocation `major_bump_grace_days` input wins when set, otherwise the org-wide GitHub Actions variable `LERIAN_LIB_MAJOR_BUMP_GRACE_DAYS` (repository, environment, or organisation scope), falling back to `3` when both are unset. Set it to `0` to disable the grace window and enforce major bumps immediately.

> **Scope:** for a Go module with a `/vN` suffix (e.g. `lib-commons/v5`), the major is fixed by the import path — the checker only ever compares against `v5.*` releases, so no major bump is ever detected there (upgrading to `/v6` is a manual import-path change). The grace window therefore applies to `v0`/`v1` modules and to libraries that publish a higher major without a `/vN` module-path suffix.

- The window is measured from the release's `published_at` date. A lib in grace shows `Grace (major bump, expires <date>)` in the report and does **not** fail the check.
- The window **auto-expires**: once the release is at least `N` days old, the lib falls back to `Outdated` on the next run and the check fails — no manual cleanup needed.
- Grace applies only to libs resolved from the releases API. Libs pinned via `.lerianstudiolibignore` (`lib@vX.Y.Z`) keep comparing against the pin as before.
- If the release date cannot be determined, the lib is enforced immediately (conservative default).

Setting the `LERIAN_LIB_MAJOR_BUMP_GRACE_DAYS` variable at organisation scope rolls a new value out across every consumer repo without touching any caller. When a specific caller needs a different window, it passes `major_bump_grace_days`, which takes precedence over the variable for that invocation.

## Secrets

| Name                    | Required | Description                                                                                                                                                                       |
|-------------------------|----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `LERIAN_LIB_READ_TOKEN` | No       | Org-scoped PAT or GitHub App token with read access to **private** LerianStudio repositories (e.g. `lib-license-go`). When unset, private libs are reported as `unknown` (warning, non-fatal). |

### Private libraries

Some Lerian libraries are internal repositories (e.g. `lib-license-go`). The default `GITHUB_TOKEN` from a consumer repo cannot read their releases — GitHub returns 404 for private repos the token has no access to. To enforce up-to-date checks on these libraries, pass an org-scoped read token via `secrets: inherit` or by mapping the secret explicitly:

```yaml
jobs:
  lerian-lib-version-check:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/lerian-lib-version-check.yml@v1.x.x
    secrets:
      LERIAN_LIB_READ_TOKEN: ${{ secrets.LERIAN_ORG_READ_TOKEN }}
```

Without the secret, the workflow still runs and enforces freshness on all **public** Lerian libs; private libs are marked `unknown` with a warning in the step summary.

## Outputs

| Name              | Description                                                          |
|-------------------|----------------------------------------------------------------------|
| `has_outdated`    | `true` if at least one direct Lerian lib is behind latest stable     |
| `outdated_count`  | Number of outdated direct Lerian libs                                |
| `grace_count`     | Number of direct Lerian libs within the major-bump grace window      |
| `has_lerian_libs` | `true` if at least one Lerian lib was detected in `go.mod`           |

## Required permissions

```yaml
permissions:
  contents: read
  pull-requests: write   # to post / update the sticky comment
```

## Failure modes

| Condition                                                | Behavior                                            |
|----------------------------------------------------------|-----------------------------------------------------|
| App has no Lerian libs in `go.mod`                       | Fail — violates company standards                   |
| One or more direct Lerian libs are outdated (minor/patch, or expired major) | Fail — bump or add to ignore file        |
| Major bump with latest release younger than the grace window | Tolerated — marked _grace_, does not fail       |
| `.lerianstudiolibignore` does not exist                  | Warning in log, proceed normally                    |
| Lib matched by ignore-skip rule                          | Skipped, marked _skipped_ in the report             |
| Lib matched by ignore-pin rule (`lib@vX.Y.Z`)            | Compared against the pin, marked _pinned_           |
| GitHub API cannot resolve latest release                 | Warning in log, marked _unknown_, does not fail     |
| `dry_run: true`                                          | Verbose report, never fails                         |

## `.lerianstudiolibignore` format

Gitignore-style, one rule per line. Lines starting with `#` are comments. Use the short module path (strip `github.com/LerianStudio/`).

```
# Skip a lib entirely (no version check)
lib-auth/v2

# Pin to a specific version — only fail if behind THIS version, not latest
lib-commons/v5@v5.3.0

# Unversioned module (v0/v1)
lib-foo
```

## Sticky PR comment

The action posts (and updates) a single comment marked with `<!-- lerian-lib-version-check -->`. Re-runs update the same comment in place — no duplicate threads accumulate across pushes.

Each row is prefixed with a status emoji, the header reflects the overall outcome (`✅ all up to date`, `🔴 action required`, or `⚠️ review needed`), and skipped/pinned rows link to the ignore-file docs so reviewers see the reason without leaving the PR.

| Status | Rendered as |
|--------|-------------|
| Up to date | `✅ Current` |
| Behind latest | `🔴 Needs update` |
| Pinned via ignore file | `📌 Pinned` |
| Skipped via ignore file | `⏭️ Skipped` |
| Latest release unresolved | `⚠️ Unknown` |
| Major bump within grace window | `🕒 Grace` |

Example:

```
## 🔴 Lerian Library Version Check — action required

| Library              | Current | Latest | Status      |
|----------------------|---------|--------|-------------|
| `lib-commons/v5`     | `v5.1.0`| `v5.5.0`| 🔴 Needs update |
| `lib-auth/v2`        | `v2.7.0`| `v2.8.0`| 🔴 Needs update |
| `lib-license-go/v2`  | `v2.3.5`| `v2.3.5`| ✅ Current |
| `lib-foo/v1`         | `v1.0.0`| `v2.0.0`| 🕒 Grace (major bump, expires 2026-07-19) |
| `lib-bar/v2`         | `v2.0.0`| _skipped_ | ⏭️ Skipped — ignore file, expires 2026-08-01 · [why?](https://github.com/LerianStudio/github-actions-shared-workflows/blob/main/docs/lerian-lib-version-check.md#lerianstudiolibignore-format) |

✅ 1 current · 🔴 2 needs update · 🕒 1 in grace · ⏭️ 1 skipped · ⚠️ 0 unknown

> Bump the outdated libraries, or add temporary entries to `.lerianstudiolibignore`.
```

Under `dry_run: true` the comment is prefixed with a `> 🧪 _Dry run — no failures enforced._` banner.

## Limitations

- **Go only.** TypeScript (`package.json`) and Helm (`Chart.yaml`) support is out of scope for the initial release.
- **Module-path → repo-name** mapping assumes the repo name equals the last non-`/vN` path segment. Modules whose repo name differs from the module path are not currently supported.
- **Public repos only.** The workflow uses the default `GITHUB_TOKEN`; all `LerianStudio/*` repos that produce stable tagged releases work out of the box.

## Related

- Issue [#408](https://github.com/LerianStudio/github-actions-shared-workflows/issues/408) — original problem statement.
