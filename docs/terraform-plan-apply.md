<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>terraform-plan-apply</h1></td>
  </tr>
</table>

Reusable Terraform plan/apply pipeline with AWS OIDC authentication and Slack
notifications. Replaces `LerianStudio/github-actions-terraform-pipeline-template`.

- On `pull_request`: runs `fmt`/`init`/`validate`/`plan` and comments the plan
  output on the PR.
- On `push` with `dry_run: false` (the default): runs `fmt`/`init`/`validate`/`apply`.
- `dry_run: true` forces plan-only on any event — it never applies, even on `push`.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `runner_type` | Runner to use for the workflow | No | `blacksmith-4vcpu-ubuntu-2404` |
| `aws_region` | AWS region to assume the OIDC role in | Yes | - |
| `environment` | Environment name (used in the backend state key and tfvars lookup) | Yes | - |
| `terraform_version` | Terraform version to install | Yes | - |
| `working_directory` | Path to the Terraform module, relative to the repo root | Yes | - |
| `terraform_resource_name` | Resource name segment used in the backend state key | Yes | - |
| `backend_bucket` | S3 bucket that stores the Terraform state | Yes | - |
| `backend_region` | AWS region of the state bucket and lock table | No | `us-east-2` |
| `backend_dynamodb_table` | DynamoDB table used for state locking | No | `terraform-lock-state` |
| `var_file` | Explicit tfvars path. Defaults to `<working_directory>/tfvars/<environment>.tfvars` when present | No | `''` |
| `pre_terraform_command` | Shell command run in the repo root after checkout, before AWS auth and Terraform (e.g. building a Lambda deployment package the Terraform config references) | No | `''` |
| `enable_slack_notify` | Send a Slack notification with the pipeline result | No | `true` |
| `dry_run` | Force plan-only, even on a push event (never applies) | No | `false` |

## Secrets

| Secret | Description | Required |
|--------|-------------|----------|
| `AWS_ROLE_TO_ASSUME` | ARN of the IAM role to assume via OIDC | Yes |
| `SLACK_WEBHOOK_URL` | Slack webhook for pipeline notifications | No |

## Outputs

| Output | Description |
|--------|-------------|
| `has_plan` | `true` when `mode=plan` (a Terraform plan was executed) |
| `has_apply` | `true` when `mode=apply` (a Terraform apply was executed) |

## Backend state key

The state object key is computed as:

```text
<environment>/<repo-name>/<terraform_resource_name>/terraform-state
```

matching the layout used by `github-actions-terraform-pipeline-template`, so
existing state files are picked up without an import/move.

## Usage

```yaml
name: "Terraform pipeline - audit"

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  id-token: write
  contents: read
  pull-requests: write

jobs:
  boundary-policy:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/terraform-plan-apply.yml@v1.58.0
    with:
      aws_region: us-east-2
      environment: audit
      terraform_version: "1.9.8"
      working_directory: src/terraform/boundary-policy
      terraform_resource_name: boundary-policy
      backend_bucket: terraform-security-foundation
    secrets:
      AWS_ROLE_TO_ASSUME: ${{ secrets.AWS_GH_OICD_TERRAFORM_ROLE }}
      SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

## Migrating from `github-actions-terraform-pipeline-template`

The old composite also supported building a Go Lambda artifact first
(`runtime: golang`, via `github-actions-go-lambda-module`). Replicate that with
`pre_terraform_command` — it runs in the same job, after checkout and before
Terraform, so any file it produces (e.g. a `function.zip` a
`data`/`filebase64sha256(...)` reads at plan time) is present when Terraform
runs. It must run in the same job as Terraform — a separate job would checkout
on a different runner and lose the build output.

```yaml
with:
  pre_terraform_command: |
    mkdir -p build src/terraform/infra
    cd src/code
    GOOS=linux GOARCH=arm64 CGO_ENABLED=0 go build -tags lambda.norpc -o ../../build/bootstrap main.go
    cd ../../build && zip function.zip bootstrap
    mv function.zip ../src/terraform/infra
```

(The old template also had a `runtime: python` option via
`github-actions-python-lambda-module`, but that action no longer exists and
its only caller has been retired — not covered here.)

The old composite required a `service-github-token` input for the PR comment.
This workflow uses the caller's ambient `GITHUB_TOKEN` instead (granted
`pull-requests: write` via the `permissions:` block above) — no extra secret
needed.
