<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>lerian-lib-version</h1></td>
  </tr>
</table>

Validates that a Go service uses up-to-date LerianStudio libraries.

The action parses `go.mod`, fetches the latest **stable** GitHub release for every direct `github.com/LerianStudio/*` dependency, compares versions, and fails when:

- any direct Lerian library is behind its latest stable release, **or**
- the service has **no** Lerian libraries at all (company-standards violation).

A sticky PR comment summarises the result. An optional `.lerianstudiolibignore` file at the repo root allows temporary skips or version pins.

## Inputs

| Input             | Description                                                                                     | Required | Default                    |
|-------------------|-------------------------------------------------------------------------------------------------|----------|----------------------------|
| `github-token`    | GitHub token used to read LerianStudio releases and post the PR comment. Use an org-scoped PAT to also read private Lerian repos (e.g. `lib-license-go`). | Yes      |                            |
| `go-mod-path`     | Path to `go.mod` relative to the repo root.                                                     | No       | `go.mod`                   |
| `ignore-file`     | Path to optional `.lerianstudiolibignore` file. Missing file is a warning, not a failure.       | No       | `.lerianstudiolibignore`   |
| `check-indirect`  | Also check transitive (`// indirect`) deps.                                                     | No       | `false`                    |
| `major-bump-grace-days` | Grace window (in days) for major-version bumps. A major bump is tolerated while the latest release is younger than this many days; minor/patch bumps are enforced immediately. Set to `0` to disable. | No | `3`                        |
| `comment-on-pr`   | Post or update a sticky comment on the PR with the result table.                                | No       | `true`                     |
| `comment-token`   | Token used to post/update the sticky PR comment. Falls back to `github-token` when empty. Must be an org-scoped PAT (e.g., `MANAGE_TOKEN`) with pull-requests:write when calling from a nested reusable workflow, because `github.token` in that context is scoped to the shared-workflows repo, not the caller. | No | `""` |
| `dry-run`         | Verbose log of all resolved versions; never fails the build.                                    | No       | `false`                    |

## Outputs

| Output             | Description                                                                       |
|--------------------|-----------------------------------------------------------------------------------|
| `has_outdated`     | `true` if at least one direct Lerian lib is behind latest stable.                 |
| `outdated_count`   | Number of outdated direct Lerian libs.                                            |
| `grace_count`      | Number of direct Lerian libs within the major-bump grace window.                  |
| `has_lerian_libs`  | `true` if at least one Lerian lib was detected in `go.mod`.                       |
| `report_path`      | Filesystem path to the generated markdown report (for downstream use).            |

## Behavior matrix

| Condition                                                | Result                                                    |
|----------------------------------------------------------|-----------------------------------------------------------|
| `go.mod` not found at `go-mod-path`                      | **Fail** with `::error`                                   |
| No `github.com/LerianStudio/*` deps in `go.mod`          | **Fail** — service must use at least one Lerian library    |
| One or more direct Lerian libs are outdated (minor/patch, or expired major) | **Fail** unless `dry-run: true`         |
| Major bump with latest release younger than `major-bump-grace-days` | Tolerated — marked `🕒 Grace`, does not fail    |
| `.lerianstudiolibignore` does not exist                  | `::warning` — proceed normally                             |
| A lib is matched by an ignore-skip rule                  | Skipped, marked `⏭️ Skipped` in the report                 |
| A lib is matched by an ignore-pin rule (`lib@vX.Y.Z`)    | Compared against the pin instead of latest, marked `📌 Pinned` |
| A lib has an active TTL (`lib\|ttl:YYYY-MM-DD`)          | Rule honored; expiry date shown in the report column        |
| A lib's TTL has expired (today ≥ TTL date)               | `::warning` — rule ignored, version check enforced         |
| TTL date format is invalid                               | `::warning` — treated as expired, version check enforced   |
| Latest stable release cannot be resolved (API error)     | `::warning` — marked `⚠️ Unknown`, does not fail            |

## `.lerianstudiolibignore` format

Gitignore-style, one rule per line. Lines starting with `#` are comments.

```
# Skip the lib entirely (no version check at all)
lib-auth/v2

# Pin to a specific version — only fail if behind THIS version, not latest
lib-commons/v5@v5.3.0

# Skip an unversioned module path (v0/v1 modules)
lib-foo

# Skip with TTL — defer until 2025-09-30, then enforce again automatically
lib-auth/v2|ttl:2025-09-30

# Pin with TTL — pin is active until 2025-09-30, then latest is enforced
lib-commons/v5@v5.3.0|ttl:2025-09-30
```

Use the **short module path** (strip `github.com/LerianStudio/`).

### TTL (time-to-live)

Append `|ttl:YYYY-MM-DD` to any rule to set an expiry date:

- **Before the TTL date** — the ignore or pin rule is honored as usual. The report shows the expiry date in the status column.
- **On or after the TTL date** — the rule is treated as if it does not exist. A `::warning` is emitted and the version check is enforced normally.
- **Invalid format** — treated as expired (safe default). A `::warning` is emitted.

This gives teams a built-in reminder mechanism: acknowledge a deferred bump with a concrete deadline, and CI re-enforces it automatically once the deadline passes.

## Usage as composite step

```yaml
jobs:
  lerian-lib-check:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6
      - name: Check Lerian library versions
        uses: LerianStudio/github-actions-shared-workflows/src/validate/lerian-lib-version@v1.x.x
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

## Usage as reusable workflow

Prefer the reusable workflow for a one-line integration:

```yaml
jobs:
  lerian-lib-check:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/lerian-lib-version-check.yml@v1.x.x
    permissions:
      contents: read
      pull-requests: write
```

## Required permissions

```yaml
permissions:
  contents: read
  pull-requests: write   # to post / update the sticky comment
```

## Implementation notes

- The action uses pure Bash + `actions/github-script` — no extra runtime is required on the runner.
- Repo names are derived from the module path by stripping `github.com/LerianStudio/` and any trailing `/vN` major-version suffix.
- Latest stable resolution paginates up to 100 releases and excludes drafts and pre-releases (`-beta`, `-rc`).
- Latest-release lookups are cached per repo within a single run to minimise API calls.
- The major-bump grace window measures release age from `published_at` and auto-expires: once the release is at least `major-bump-grace-days` old, the lib falls back to `Outdated`. It applies to API-resolved (unpinned) libs only. Because a `/vN` module is pinned to its major by the import path, the window effectively covers `v0`/`v1` modules and libs that publish a higher major without a `/vN` suffix.
- Repo-name resolution assumes one repo per module. Modules whose repo name differs from the path segment are not currently supported.
