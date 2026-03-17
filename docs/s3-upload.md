<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>s3-upload</h1></td>
  </tr>
</table>

Reusable workflow for uploading files to AWS S3 with automatic environment-based folder routing and OIDC authentication.

## What it does

Uploads files matching a glob pattern to an S3 bucket, organized by environment folder. The environment is detected automatically from the git ref/tag or can be set manually.

| Ref / Tag | Environment folder |
|---|---|
| `develop` branch or `*-beta*` tag | `development/` |
| `release-candidate` branch or `*-rc*` tag | `staging/` |
| `main` branch or `vX.Y.Z` tag | `production/` |

## Inputs

| Input | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `runner_type` | `string` | No | `blacksmith-4vcpu-ubuntu-2404` | Runner to use for the workflow |
| `s3_bucket` | `string` | **Yes** | — | S3 bucket name (without `s3://` prefix) |
| `file_pattern` | `string` | **Yes** | — | Glob pattern for files to upload |
| `s3_prefix` | `string` | No | `""` | Optional prefix inside the environment folder |
| `aws_region` | `string` | No | `us-east-2` | AWS region |
| `environment_detection` | `string` | No | `tag_suffix` | Detection strategy: `tag_suffix` or `manual` |
| `manual_environment` | `string` | No | — | Environment override: `development`, `staging`, or `production` |
| `flatten` | `boolean` | No | `true` | Upload only filenames (discard directory structure) |
| `dry_run` | `boolean` | No | `false` | Preview uploads without applying them |

## Secrets

| Secret | Required | Description |
|---|---|---|
| `AWS_ROLE_ARN` | **Yes** | ARN of the IAM role to assume via OIDC for S3 access |

## Usage

### Upload init data files

```yaml
jobs:
  upload:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/s3-upload.yml@v1.0.0
    with:
      s3_bucket: "lerian-casdoor-init-data"
      file_pattern: "init/casdoor/init_data*.json"
    secrets:
      AWS_ROLE_ARN: ${{ secrets.AWS_INIT_DATA_ROLE_ARN }}
```

### Upload migration files with custom prefix

```yaml
jobs:
  upload:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/s3-upload.yml@v1.0.0
    with:
      s3_bucket: "lerian-migration-files"
      file_pattern: "init/casdoor-migrations/migrations/*.sql"
      s3_prefix: "casdoor-migrations"
    secrets:
      AWS_ROLE_ARN: ${{ secrets.AWS_MIGRATIONS_ROLE_ARN }}
```

### Dry run (preview only)

```yaml
# Use @develop or your feature branch to validate before releasing
jobs:
  preview:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/s3-upload.yml@develop
    with:
      s3_bucket: "lerian-casdoor-init-data"
      file_pattern: "init/casdoor/init_data*.json"
      dry_run: true
    secrets:
      AWS_ROLE_ARN: ${{ secrets.AWS_INIT_DATA_ROLE_ARN }}
```

### Manual environment override

```yaml
jobs:
  upload:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/s3-upload.yml@v1.0.0
    with:
      s3_bucket: "lerian-casdoor-init-data"
      file_pattern: "init/casdoor/init_data*.json"
      environment_detection: "manual"
      manual_environment: "staging"
    secrets:
      AWS_ROLE_ARN: ${{ secrets.AWS_INIT_DATA_ROLE_ARN }}
```

### Preserve directory structure

```yaml
jobs:
  upload:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/s3-upload.yml@v1.0.0
    with:
      s3_bucket: "lerian-migration-files"
      file_pattern: "init/casdoor-migrations/migrations/*.sql"
      flatten: false
    secrets:
      AWS_ROLE_ARN: ${{ secrets.AWS_MIGRATIONS_ROLE_ARN }}
```

## Permissions

```yaml
permissions:
  id-token: write
  contents: read
```
