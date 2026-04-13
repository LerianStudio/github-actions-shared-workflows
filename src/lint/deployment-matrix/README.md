<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>deployment-matrix</h1></td>
  </tr>
</table>

Validate the deployment matrix manifest at `config/deployment-matrix.yaml` (or any custom path). This manifest is the source of truth consumed by the `gitops-update.yml` reusable workflow to decide which apps deploy to which Kubernetes clusters.

Checks performed:

**Schema**
- `version` is an integer equal to `1`
- `apps.registry` is a list of non-empty strings
- `clusters` is a mapping of `<cluster-name>` → cluster spec
- Each `clusters.<name>.apps` is a list of non-empty strings

**Integrity**
- Every app listed in any `clusters.<name>.apps` is declared in `apps.registry` (typo gate)
- No duplicates inside `apps.registry`
- No duplicates inside any `clusters.<name>.apps`

**Hygiene (warnings, not errors)**
- Apps in `apps.registry` not referenced by any cluster are flagged — likely pre-onboarding entries, but worth reviewing to avoid dead registrations

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `manifest-file` | Path to the deployment matrix YAML manifest | No | `config/deployment-matrix.yaml` |

## Usage as composite step

```yaml
jobs:
  deployment-matrix:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - name: Checkout
        uses: actions/checkout@v6

      - name: Deployment Matrix Lint
        uses: LerianStudio/github-actions-shared-workflows/src/lint/deployment-matrix@v1.x.x
        with:
          manifest-file: config/deployment-matrix.yaml
```

## Required permissions

```yaml
permissions:
  contents: read
```
