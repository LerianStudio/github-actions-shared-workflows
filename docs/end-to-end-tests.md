<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>end-to-end-tests</h1></td>
  </tr>
</table>

Reusable workflow that runs the [`LerianStudio/end-to-end`](https://github.com/LerianStudio/end-to-end)
gray-box/black-box suite (Go + Allure 3) against an already-deployed environment,
then uploads the static Allure report to the `lerian-e2e-artifacts` S3 bucket —
the same bucket/role the JS products (e.g. product-console) already use, read by
Palantir (self-service-testing)'s E2E page.

## Features

- **Runs the shared e2e suite** against a deployed environment (no local stack)
- **Per-component scoping**: only the module(s) actually rebuilt this run are
  exercised (via the `built_apps` matrix from `build.yml`)
- **Tag-driven environment**: `beta -> dev`, `rc -> stg`, else `prd`, combined
  with the caller's tenancy (`st`/`mt`)
- **Allure report to S3**: `s3://<bucket>/<repo>/<channel>/<tag>/<module>/`,
  plus a GitHub Actions artifact (30-day retention)
- **Ephemeral credentials**: per-module `.env` files are generated at runtime
  from secrets and removed via an `EXIT` trap before the runner is released
- **`dry_run`**: resolve and print the plan (environment, modules, S3 targets)
  without writing to S3

## Inputs

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `modules` | string | yes | — | Comma-separated candidate modules (e.g. `midaz-ledger,midaz-crm`). Each maps to `./cases/<module>/...`. Narrowed to `built_apps` when set. |
| `built_apps` | string | no | `[]` | JSON array of components built this run (`build.yml`'s matrix output). Only candidates whose name appears here run. Empty runs every candidate. |
| `tenancy` | string | no | `st` | Tenancy mode of the deployed environment — `st` or `mt`. |
| `service_domain` | string | no | `lerian.net` | Base domain; URLs are `https://<app>.<base_env>-<tenancy>.<service_domain>`. |
| `s3_bucket` | string | no | `lerian-e2e-artifacts` | S3 bucket the Allure report is uploaded to. |
| `go_version` | string | no | `1.25` | Go version (should match the e2e repo `go.mod`). |
| `node_version` | string | no | `20` | Node.js version (for the Allure 3 CLI). |
| `runner_type` | string | no | `eveo-lxc-runners` | Runner. Needs reach to the deployed environment (matches `api-dog-e2e-tests` and the ungoliant job). |
| `timeout` | string | no | `600s` | Per-run Go test timeout (`make test TIMEOUT=`). |
| `dry_run` | boolean | no | `false` | Preview only — print resolved plan, skip S3 uploads. Tests still run. |

## Outputs

| Name | Description |
|------|-------------|
| `has_modules` | `"true"` if at least one candidate module was selected to run; `"false"` when no built component matched a candidate and the run was a no-op. |

## Secrets

| Name | Required | Description |
|------|----------|-------------|
| `e2e_repo_token` | yes | Token with read access to the private e2e repository. The `go-release.yml` caller feeds it the org `MANAGE_TOKEN` (the same token gitops-update uses), so no dedicated e2e token is needed. |
| `aws_e2e_artifacts_role_arn` | no | IAM role assumed via OIDC to upload to S3. Unset — S3 upload skipped, only the GitHub artifact is produced. |
| `admin_tenant_1_username` / `admin_tenant_1_password` | no | Tenant 1 login for the deployed environment. |
| `admin_tenant_2_username` / `admin_tenant_2_password` | no | Tenant 2 login (multi-tenant only). |

## Usage

### Direct call

```yaml
e2e:
  permissions:
    id-token: write
    contents: read
  uses: LerianStudio/github-actions-shared-workflows/.github/workflows/end-to-end-tests.yml@vX.Y.Z
  with:
    modules: "midaz-ledger,midaz-crm"
    tenancy: st
  secrets:
    e2e_repo_token: ${{ secrets.MANAGE_TOKEN }}   # any token with read access to the suite repo
    aws_e2e_artifacts_role_arn: ${{ secrets.AWS_E2E_ARTIFACTS_ROLE_ARN }}
    admin_tenant_1_username: ${{ secrets.E2E_ADMIN_TENANT_1_USERNAME }}
    admin_tenant_1_password: ${{ secrets.E2E_ADMIN_TENANT_1_PASSWORD }}
```

### Via `go-release.yml`

`go-release.yml` wires this in as an opt-in `e2e_tests` job that runs after a
successful `update_gitops` on a tag push, scoped to the component(s) that built:

```yaml
jobs:
  pipeline:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-release.yml@vX.Y.Z
    with:
      enable_e2e_tests: true
      e2e_modules: "midaz-ledger,midaz-crm"
      e2e_tenancy: st
    secrets: inherit
```

The `go-release.yml` caller forwards `build.yml`'s matrix as `built_apps`, so a
ledger-only change runs only `midaz-ledger`, a crm-only change runs only
`midaz-crm`, and a change touching both (or a `shared_paths` hit) runs both.

## S3 layout

```
s3://<s3_bucket>/<repo>/<channel>/<tag>/<module>/
```

- `<channel>` is derived from the tag's prerelease identifier: `-beta.*` -> `beta`,
  `-rc.*` -> `rc`, otherwise `main` — the same convention the JS products' e2e job
  uses.
- `<module>` is the per-module leaf (one run can cover several modules), mirroring
  playwright's fixed `playwright-report` leaf.
