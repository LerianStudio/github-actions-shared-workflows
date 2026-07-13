<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>go-lambda-release</h1></td>
  </tr>
</table>

Reusable workflow that builds a Go AWS Lambda into a `provided.al2*` `bootstrap`
zip artifact (via the [`build-go-lambda`](../src/build/build-go-lambda) composite)
and uploads it to a versioned S3 bucket using OIDC. Designed to run on a tag push
so the artifact is stored under a per-version key.

## What it does

1. Checks out the caller repository.
2. Compiles the Go main package to a `bootstrap` binary (default `linux/arm64`,
   symbols stripped, `lambda.norpc` tag) and zips it.
3. Resolves the release version (from the pushed tag or `inputs.version`).
4. Uploads the zip to `s3://<s3_bucket>/<s3_key_prefix>/<version>/<artifact_name>`
   and returns the S3 object version id.

On `dry_run: true` the artifact is built and the target key is resolved, but
nothing is uploaded.

## Inputs

| Input | Type | Required | Default | Description |
|---|---|:---:|---|---|
| `go_version` | `string` | No | `1.23` | Go version used to build the binary |
| `main_package` | `string` | No | `.` | Path to the Go main package (e.g. `./cmd/authorizer`) |
| `goarch` | `string` | No | `arm64` | Target architecture (`arm64` or `amd64`) |
| `artifact_name` | `string` | No | `bootstrap.zip` | File name of the generated zip |
| `version` | `string` | No | `""` | Release version for the S3 key; defaults to the pushed git tag |
| `s3_bucket` | `string` | **Yes** | — | Target S3 bucket (without `s3://`) |
| `s3_key_prefix` | `string` | **Yes** | — | Key prefix; final key is `<prefix>/<version>/<artifact_name>` |
| `aws_region` | `string` | No | `us-east-2` | AWS region of the bucket |
| `dry_run` | `boolean` | No | `false` | Build and resolve the key without uploading |

## Secrets

| Secret | Required | Description |
|---|---|---|
| `AWS_ROLE_ARN` | **Yes** | ARN of the IAM role to assume via OIDC for the S3 upload |

## Outputs

| Output | Description |
|---|---|
| `version` | Resolved release version |
| `s3_key` | Full S3 key of the uploaded artifact |
| `s3_version_id` | S3 object version id (empty on dry run) |
| `binary_sha256` | SHA-256 checksum of the built `bootstrap` binary |

## Usage

### Release on tag push

```yaml
name: Release
on:
  push:
    tags: ["v*"]
jobs:
  release:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-lambda-release.yml@v1.0.0
    with:
      main_package: ./cmd/authorizer
      artifact_name: authorizer.zip
      s3_bucket: lerian-lambda-artifacts
      s3_key_prefix: casdoor-authorizer
    secrets:
      AWS_ROLE_ARN: ${{ secrets.AWS_LAMBDA_ARTIFACTS_ROLE_ARN }}
```

The artifact is uploaded to
`s3://lerian-lambda-artifacts/casdoor-authorizer/v1.2.3/authorizer.zip`.

### Dry run (preview only)

```yaml
# Use @develop or your feature branch to validate before releasing
jobs:
  preview:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-lambda-release.yml@develop
    with:
      main_package: ./cmd/authorizer
      artifact_name: authorizer.zip
      s3_bucket: lerian-lambda-artifacts
      s3_key_prefix: casdoor-authorizer
      version: v0.0.0-test
      dry_run: true
    secrets:
      AWS_ROLE_ARN: ${{ secrets.AWS_LAMBDA_ARTIFACTS_ROLE_ARN }}
```

### Explicit version (non-tag ref)

```yaml
jobs:
  release:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-lambda-release.yml@v1.0.0
    with:
      main_package: ./cmd/authorizer
      artifact_name: authorizer.zip
      s3_bucket: lerian-lambda-artifacts
      s3_key_prefix: casdoor-authorizer
      version: v1.2.3
    secrets:
      AWS_ROLE_ARN: ${{ secrets.AWS_LAMBDA_ARTIFACTS_ROLE_ARN }}
```

## Permissions

```yaml
permissions:
  id-token: write
  contents: read
```

The target S3 bucket should have versioning enabled so each upload produces a
distinct object version (`s3_version_id`).
