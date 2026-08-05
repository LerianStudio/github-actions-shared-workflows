<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>s3-sync</h1></td>
  </tr>
</table>

Composite action that syncs a **built single-page application** to an S3 bucket root with differentiated `Cache-Control`:

1. Fingerprinted assets (everything except `*.html`) sync **first** with an immutable, long-lived `Cache-Control` and `--delete` to prune stale objects.
2. `*.html` syncs **last** with `no-store` — so a freshly-served `index.html` never references assets that are not yet uploaded.

Requires AWS credentials to already be configured in the environment (e.g. via `aws-actions/configure-aws-credentials` OIDC in the calling job) and the AWS CLI to be present (see [`setup/aws-cli`](../../setup/aws-cli)). It performs **no authentication itself** — secrets stay in the reusable workflow.

## Why custom `aws` shell (not a Marketplace action)

Marketplace S3-sync actions (e.g. `jakejarvis/s3-sync-action`) run a **single** `aws s3 sync` and expose one `Cache-Control` for the whole upload. This composite needs a **two-pass** sync — immutable fingerprinted assets first (with `--delete`), then `*.html` uploaded **last** with `no-store` — so an `index.html` is never served referencing assets that aren't uploaded yet. No maintained Marketplace action models that ordering, and driving `aws` directly matches the sibling [`s3-upload.yml`](../../../.github/workflows/s3-upload.yml) convention in this repo. Authentication is deliberately left to `aws-actions/configure-aws-credentials` (OIDC) in the calling workflow.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `dist-directory` | Build output directory to sync, relative to the repo root | Yes | — |
| `s3-bucket` | Destination S3 bucket name (without `s3://`); objects sync to the bucket **root** | Yes | — |
| `assets-cache-control` | `Cache-Control` applied to fingerprinted assets (all non-`*.html`) | No | `public,max-age=31536000,immutable` |
| `html-cache-control` | `Cache-Control` applied to `*.html`, uploaded last | No | `no-store` |
| `dry-run` | Preview both syncs with `--dryrun` (no objects written) | No | `false` |

## Usage as composite step

```yaml
steps:
  - name: Configure AWS credentials (OIDC)
    uses: aws-actions/configure-aws-credentials@e6de054238d6b7531b4efff3b6587d9aade6a06c # v6.2.3
    with:
      role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
      aws-region: us-east-1

  - name: Sync SPA to S3
    uses: ./src/deploy/s3-sync
    with:
      dist-directory: frontend/dist-customer
      s3-bucket: my-spa-bucket
      dry-run: ${{ inputs.dry_run }}
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
