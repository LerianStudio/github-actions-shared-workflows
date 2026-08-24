<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>terraform-plan-apply</h1></td>
  </tr>
</table>

Composite action that runs `terraform fmt/init/validate` against a remote S3
backend, then either plans (posting the output as a PR comment) or applies.
Does not perform AWS authentication or notifications — those are the caller's
responsibility (see the `terraform-plan-apply.yml` reusable workflow for the
full orchestration).

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `working-directory` | Path to the Terraform module, relative to the repo root | Yes | - |
| `environment` | Environment name, used to look up the default tfvars file | Yes | - |
| `terraform-version` | Terraform version to install | Yes | - |
| `mode` | `plan` or `apply` | Yes | - |
| `backend-bucket` | S3 bucket that stores the Terraform state | Yes | - |
| `backend-key` | Full state object key within the backend bucket | Yes | - |
| `backend-region` | AWS region of the state bucket and lock table | No | `us-east-2` |
| `backend-dynamodb-table` | DynamoDB table used for state locking | No | `terraform-lock-state` |
| `var-file` | Explicit tfvars path. Defaults to `<working-directory>/tfvars/<environment>.tfvars` when present | No | `""` |
| `github-token` | Token used to comment the plan output on the pull request | Yes | - |
| `pr-number` | Pull request number to comment on. Comment step is skipped when empty | No | `""` |

## Outputs

| Output | Description |
|--------|-------------|
| `has-plan` | `true` when `mode=plan` (a Terraform plan was executed) |
| `has-apply` | `true` when `mode=apply` (a Terraform apply was executed) |

Plan/apply failures also surface via the step exit code.

## Usage as composite step

```yaml
jobs:
  terraform:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    permissions:
      id-token: write
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v6
        with:
          fetch-depth: 0

      - uses: aws-actions/configure-aws-credentials@e6de054238d6b7531b4efff3b6587d9aade6a06c # v6.2.3
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_TO_ASSUME }}
          aws-region: us-east-2

      - uses: LerianStudio/github-actions-shared-workflows/src/deploy/terraform-plan-apply@v1
        with:
          working-directory: src/terraform/boundary-policy
          environment: audit
          terraform-version: "1.9.8"
          mode: ${{ github.event_name == 'pull_request' && 'plan' || 'apply' }}
          backend-bucket: terraform-security-foundation
          backend-key: audit/${{ github.event.repository.name }}/boundary-policy/terraform-state
          github-token: ${{ github.token }}
          pr-number: ${{ github.event.pull_request.number }}
```

## Usage via reusable workflow

```yaml
jobs:
  boundary-policy:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/terraform-plan-apply.yml@v1
    with:
      aws_region: us-east-2
      environment: audit
      terraform_version: "1.9.8"
      working_directory: src/terraform/boundary-policy
      terraform_resource_name: boundary-policy
      backend_bucket: terraform-security-foundation
    secrets: inherit
```

Prefer the reusable workflow over calling this composite directly — it handles
checkout, AWS OIDC auth, mode selection and Slack notification (see
`docs/terraform-plan-apply.md`).

## Why `hashicorp/setup-terraform`

It is the Terraform team's own action, keeps the binary version pinned per
caller (via `terraform-version`) instead of relying on whatever the runner
image ships, and is already the de facto standard across the org's Terraform
callers being migrated to this composite.

## Required permissions

```yaml
permissions:
  id-token: write
  contents: read
  pull-requests: write
```

`id-token: write` is required by the caller's AWS OIDC step (not by this
composite directly). `pull-requests: write` is required only when `pr-number`
is set.
