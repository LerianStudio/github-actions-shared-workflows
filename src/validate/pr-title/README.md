<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>pr-title</h1></td>
  </tr>
</table>

Validates PR title follows [Conventional Commits](https://www.conventionalcommits.org/) format using [action-semantic-pull-request](https://github.com/amannn/action-semantic-pull-request).

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `github-token` | GitHub token for PR status checks | Yes | |
| `types` | Allowed commit types (newline-separated) | No | `feat fix docs style refactor perf test chore ci build revert` |
| `scopes` | Allowed scopes (newline-separated, empty = any) | No | `""` |
| `require-scope` | Require scope in PR title | No | `false` |

## Usage as composite step

```yaml
jobs:
  pr-title:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - name: Validate PR Title
        uses: LerianStudio/github-actions-shared-workflows/src/validate/pr-title@v1.x.x
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

## Usage as reusable workflow

Called via the `pr-validation.yml` reusable workflow:

```yaml
jobs:
  validate:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-validation.yml@v1.x.x
    with:
      pr_title_types: |
        feat
        fix
        docs
    secrets: inherit
```

## Required permissions

```yaml
permissions:
  pull-requests: read
```
