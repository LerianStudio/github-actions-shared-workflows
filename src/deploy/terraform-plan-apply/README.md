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

None. Plan/apply failures surface via the step exit code.

## Usage as composite step

```yaml
steps:
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

Prefer the `terraform-plan-apply.yml` reusable workflow over calling this
composite directly — it handles checkout, AWS OIDC auth, mode selection and
Slack notification.

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
