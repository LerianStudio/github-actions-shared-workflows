<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>aws-cli</h1></td>
  </tr>
</table>

Composite action that ensures the AWS CLI v2 is available on the runner. It is a
no-op when `aws` is already on `PATH` or a cached user-local install exists;
otherwise it installs a **pinned** version and verifies the vendor **GnuPG
signature** (key imported by fingerprint from a keyserver) before running the
installer. Designed for self-hosted runners, which do not ship the AWS CLI.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `version` | AWS CLI v2 version to install (pinned — bump to update) | No | `2.36.2` |
| `gpg-fingerprint` | Full fingerprint of the AWS CLI team signing key used to verify the installer | No | `FB5DB77FD5C118B80511ADA8A6310ACC4672475C` |
| `install-dir` | Directory passed to the AWS installer `-i` flag (empty = `$HOME/.local/aws-cli`) | No | `""` |
| `bin-dir` | Directory passed to `-b` and appended to `PATH` (empty = `$HOME/.local/bin`) | No | `""` |

## Outputs

None. On success the AWS CLI is on `PATH` (via `$GITHUB_PATH`).

## Usage as composite step

```yaml
steps:
  - name: Ensure AWS CLI
    uses: LerianStudio/github-actions-shared-workflows/src/setup/aws-cli@v1
```

## Usage via reusable workflow

```yaml
jobs:
  e2e:
    runs-on: eveo-lxc-runners
    steps:
      - uses: LerianStudio/github-actions-shared-workflows/src/setup/aws-cli@v1
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-2
      - run: aws s3 cp ./out s3://bucket/prefix/ --recursive
```

## Required permissions

The install step needs only network access:

```yaml
permissions:
  contents: read
```

`gpg` and `unzip` must be present on the runner (both are standard on the eveo
LXC runners).
