<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>cloudfront-invalidate</h1></td>
  </tr>
</table>

Composite action that creates a **CloudFront invalidation** for the given paths after a deploy. When `dry-run` is `true`, the invalidation is skipped and the intended action is logged instead.

Requires AWS credentials to already be configured in the environment (e.g. via `aws-actions/configure-aws-credentials` OIDC in the calling job) and the AWS CLI to be present (see [`setup/aws-cli`](../../setup/aws-cli)). It performs **no authentication itself** — secrets stay in the reusable workflow.

## Why custom `aws` shell (not a Marketplace action)

A single `aws cloudfront create-invalidation` call is simpler and more auditable than pulling a wrapper action, needs no extra pinning surface, and reuses the AWS credentials already assumed for the S3 sync in the same job. It also gives the `dry-run` short-circuit (log instead of invalidate) for free. Authentication is deliberately left to `aws-actions/configure-aws-credentials` (OIDC) in the calling workflow.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `distribution-id` | CloudFront distribution ID to invalidate | Yes | — |
| `paths` | Space-separated list of invalidation paths | No | `/ /index.html` |
| `dry-run` | Skip the invalidation and log what would happen | No | `false` |

## Usage as composite step

```yaml
name: Deploy SPA
on:
  push:
    branches: [main]
permissions:
  contents: read
  id-token: write # AWS OIDC
jobs:
  deploy:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      # Build + upload your SPA first…

      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@e6de054238d6b7531b4efff3b6587d9aade6a06c # v6.2.3
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
          aws-region: us-east-1

      - name: Invalidate CloudFront
        uses: LerianStudio/github-actions-shared-workflows/src/deploy/cloudfront-invalidate@develop
        with:
          distribution-id: E1234567890ABC
          dry-run: false
```

## Usage via reusable workflow

```yaml
jobs:
  deploy:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/spa-deploy.yml@develop
    with:
      build_command: npm run build:customer
      dist_directory: frontend/dist-customer
      aws_region: us-east-1
      s3_bucket: my-spa-bucket
      cloudfront_distribution_id: E1234567890ABC
    secrets: inherit
```

## Required permissions

The **calling job** must grant OIDC access so credentials can be assumed before this step:

```yaml
permissions:
  contents: read
  id-token: write # AWS OIDC
```
