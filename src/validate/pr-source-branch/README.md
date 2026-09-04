<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>pr-source-branch</h1></td>
  </tr>
</table>

Validates that PRs to protected branches come from allowed source branches. Supports exact branch names and prefix patterns (e.g., `hotfix/*`).

On failure, upserts a single PR comment (identified by the `<!-- pr-source-branch-validation -->` marker) instead of stacking a new `REQUEST_CHANGES` review on every commit. When the source branch becomes valid in a later run, the same comment is rewritten to a passing message. The job's failure status (and any branch-protection check requirement) still gates merges.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `github-token` | GitHub token with pull-requests write permission | Yes | |
| `allowed-branches` | Allowed source branches (pipe-separated, supports `*` wildcard) | No | `hotfix/*\|release-candidate` |
| `target-branches` | Target branches that require validation (pipe-separated) | No | `main` |
| `branch-rules` | Per-target rules as JSON. A listed target uses its own patterns and is validated even when `target-branches` omits it | No | `''` |
| `dry-run` | When true, validate without upserting the failure comment | No | `false` |

## Per-target rules

`allowed-branches` and `target-branches` describe one rule applied to every protected branch. When protected branches accept different sources, pass `branch-rules` instead:

```yaml
branch-rules: |
  {
    "main": "release-candidate|hotfix/*",
    "release-candidate": "develop-*|hotfix/*"
  }
```

Precedence: a target named in `branch-rules` overrides **both** flat inputs — its own patterns replace `allowed-branches`, and it is validated even if `target-branches` does not list it. Targets absent from the map keep following the flat inputs, so an empty `branch-rules` behaves exactly as before.

Each value must be a **string** of pipe-separated patterns. A non-string value (`null`, an array, a boolean) fails the run rather than being coerced into a pattern that would silently match nothing.

## Usage as composite step

```yaml
jobs:
  source-branch:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - name: Validate Source Branch
        uses: LerianStudio/github-actions-shared-workflows/src/validate/pr-source-branch@v1.x.x
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          allowed-branches: "develop|hotfix/*"
          target-branches: "main"
```

## Usage as reusable workflow

Called via the `pr-validation.yml` reusable workflow:

```yaml
jobs:
  validate:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-validation.yml@v1.x.x
    with:
      enforce_source_branches: true
      allowed_source_branches: "develop|hotfix/*"
      target_branches_for_source_check: "main"
    secrets: inherit
```

## Required permissions

```yaml
permissions:
  pull-requests: write
  issues: write
```
