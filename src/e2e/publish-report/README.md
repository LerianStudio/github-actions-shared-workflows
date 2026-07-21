<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>publish-report</h1></td>
  </tr>
</table>

Composite action that uploads each module's Allure report to S3 under
`<bucket>/<repo>/<channel>/<tag>/<module>/` — the layout Palantir
(self-service-testing) reads. The channel is derived from the tag's prerelease
identifier (`-beta.*`→beta, `-rc.*`→rc, else main). In `dry-run` it prints the
resolved destinations and uploads nothing. AWS credentials must already be
configured by the caller.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `modules` | Comma-separated modules whose `reports/allure-report-<module>/` dirs are uploaded | Yes | — |
| `s3-bucket` | Destination S3 bucket | Yes | — |
| `repo-name` | Repository name for the S3 path (`github.event.repository.name`) | Yes | — |
| `tag-name` | Release tag (`github.ref_name`); selects the channel | Yes | — |
| `dry-run` | `"true"` prints destinations and skips uploads | No | `"false"` |
| `has-role` | `"true"`/`"false"` — only annotates dry-run output when no role is set | No | `"false"` |

## Outputs

None.

## Usage as composite step

```yaml
steps:
  - uses: aws-actions/configure-aws-credentials@v4
    with:
      role-to-assume: ${{ secrets.AWS_E2E_ARTIFACTS_ROLE_ARN }}
      aws-region: us-east-2
  - name: Publish E2E report
    uses: LerianStudio/github-actions-shared-workflows/src/e2e/publish-report@v1
    with:
      modules: ${{ steps.plan.outputs.modules }}
      s3-bucket: lerian-e2e-artifacts
      repo-name: ${{ github.event.repository.name }}
      tag-name: ${{ github.ref_name }}
```

## Usage via reusable workflow

Used internally by `end-to-end-tests.yml`.

## Required permissions

Uploading via AWS OIDC requires:

```yaml
permissions:
  id-token: write
  contents: read
```
