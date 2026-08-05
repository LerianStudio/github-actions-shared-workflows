<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>spa-deploy</h1></td>
  </tr>
</table>

Reusable workflow that **builds a single-page application and deploys it to S3 + CloudFront** with differentiated `Cache-Control` and cache invalidation.

It fills the gap left by [`s3-upload.yml`](./s3-upload.md), which cannot deploy a built SPA: it does not build, takes no artifact, forces an `<env>/` sub-folder, sets no `Cache-Control`, does no `--delete` sync, and does no CloudFront invalidation.

## What it does

1. `checkout` (SHA-pinned, `persist-credentials: false`).
2. `setup-node` with npm cache keyed on `<working_directory>/package-lock.json`.
3. `npm ci` in `working_directory`.
4. Run `build_command` in `working_directory`.
5. Verify `dist_directory` exists and is non-empty.
6. `configure-aws-credentials` via OIDC `role-to-assume` — **never static keys**.
7. `aws s3 sync --delete` of fingerprinted assets with `Cache-Control: public,max-age=31536000,immutable` (excludes `*.html`).
8. `aws s3 sync` of `*.html` **last**, with `Cache-Control: no-store` — so a freshly-served `index.html` never references assets that are not yet uploaded.
9. `aws cloudfront create-invalidation --paths "/" "/index.html"`.

The bucket root is the sync target (no forced environment sub-folder). `dry_run: true` runs both syncs with `--dryrun` and skips the invalidation.

## Inputs

| Input | Description | Required | Default |
|---|---|---|---|
| `runner_type` | Runner to use (overridden by `vars.GENERAL_RUNNERS` when set) | No | `blacksmith-4vcpu-ubuntu-2404` |
| `working_directory` | Directory with `package.json` / SPA source (`npm ci` + build run here) | No | `frontend` |
| `build_command` | Command that produces the production build (e.g. `npm run build:customer`) | Yes | — |
| `dist_directory` | Build output directory to sync, relative to the repo root (e.g. `frontend/dist-customer`) | Yes | — |
| `aws_region` | AWS region of the S3 bucket and CloudFront distribution | Yes | — |
| `s3_bucket` | Destination S3 bucket name (without `s3://`); objects sync to the bucket **root** | Yes | — |
| `cloudfront_distribution_id` | CloudFront distribution ID to invalidate after upload | Yes | — |
| `node_version` | Node.js version for `setup-node` | No | `22` |
| `dry_run` | Preview the sync (`aws s3 sync --dryrun`) and skip invalidation | No | `false` |

## Secrets

| Secret | Description | Required |
|---|---|---|
| `AWS_DEPLOY_ROLE_ARN` | ARN of the IAM role to assume via OIDC for S3 + CloudFront access | Yes |

## Required permissions

The **caller job** must grant:

```yaml
permissions:
  contents: read
  id-token: write # AWS OIDC
```

## Usage — caller workflow

> A job that calls a reusable workflow cannot set `environment:`. If your bucket/role
> values live under a GitHub Environment, either promote them to repository-level
> `vars`/`secrets` or wrap this in an environment-scoped job that re-dispatches.

```yaml
# Testing — point at develop or the feature branch
name: Frontend Deploy
on:
  push:
    branches: [develop]
permissions:
  contents: read
  id-token: write
jobs:
  deploy:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/spa-deploy.yml@develop
    with:
      working_directory: frontend
      build_command: npm run build:customer
      dist_directory: frontend/dist-customer
      aws_region: ${{ vars.AWS_REGION }}
      s3_bucket: ${{ vars.SPA_S3_BUCKET }}
      cloudfront_distribution_id: ${{ vars.CLOUDFRONT_DISTRIBUTION_ID }}
    secrets:
      AWS_DEPLOY_ROLE_ARN: ${{ secrets.FRONTEND_DEPLOY_ROLE_ARN }}
```

```yaml
# Production — always pin to a released tag
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/spa-deploy.yml@v1.51.0
```
