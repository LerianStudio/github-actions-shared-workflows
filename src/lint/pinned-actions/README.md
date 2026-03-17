<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>pinned-actions</h1></td>
  </tr>
</table>

Ensure all third-party GitHub Action references use pinned versions (`@vX.Y.Z` or `@sha`), not mutable refs like `@main` or `@master`.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `files` | Space-separated list of workflow/composite files to check | No | `` |
| `ignore-patterns` | Pipe-separated org/owner prefixes to skip (e.g. internal actions) | No | `LerianStudio/` |

## Usage as composite step

```yaml
- name: Checkout
  uses: actions/checkout@v4

- name: Pinned Actions Check
  uses: LerianStudio/github-actions-shared-workflows/src/lint/pinned-actions@v1.2.3
  with:
    files: ".github/workflows/ci.yml .github/workflows/deploy.yml"
    ignore-patterns: "LerianStudio/|my-org/"
```

## Usage via reusable workflow

```yaml
jobs:
  lint:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-lint.yml@v1.2.3
    secrets: inherit
```

## Required permissions

```yaml
permissions:
  contents: read
```
