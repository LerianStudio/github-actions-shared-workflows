<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>pr-description</h1></td>
  </tr>
</table>

Validates that the PR description has real content beyond template boilerplate:

- **Description section**: extracts content under `## Description`, strips HTML comments, and checks minimum length
- **Type of Change**: verifies at least one checkbox is checked (`- [x]`)

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `min-length` | Minimum content length in characters (after stripping template boilerplate) | No | `30` |

## Usage as composite step

```yaml
jobs:
  pr-description:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - name: Validate PR Description
        uses: LerianStudio/github-actions-shared-workflows/src/validate/pr-description@v1.x.x
        with:
          min-length: "50"
```

## Required permissions

```yaml
permissions:
  pull-requests: read
```
