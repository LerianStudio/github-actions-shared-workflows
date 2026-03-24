<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>pr-source-branch</h1></td>
  </tr>
</table>

Validates that PRs to protected branches come from allowed source branches. Supports exact branch names and prefix patterns (e.g., `hotfix/*`).

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `github-token` | GitHub token with pull-requests write permission | Yes | |
| `allowed-branches` | Allowed source branches (pipe-separated, supports `*` wildcard) | No | `develop\|release-candidate\|hotfix/*` |
| `target-branches` | Target branches that require validation (pipe-separated) | No | `main` |
| `dry-run` | When true, validate without posting REQUEST_CHANGES review | No | `false` |

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
```
