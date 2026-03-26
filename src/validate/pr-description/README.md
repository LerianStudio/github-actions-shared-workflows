<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>pr-description</h1></td>
  </tr>
</table>

Validates that the PR template checkboxes are properly filled:

- **Type of Change**: at least one checkbox must be checked (`- [x]`)
- **Testing**: at least one checkbox must be checked (`- [x]`)

## Inputs

None.

## Usage as composite step

```yaml
jobs:
  pr-description:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - name: Validate PR Description
        uses: LerianStudio/github-actions-shared-workflows/src/validate/pr-description@v1.x.x
```

## Required permissions

```yaml
permissions:
  pull-requests: read
```
