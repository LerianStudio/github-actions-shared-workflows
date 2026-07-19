<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>run-suite</h1></td>
  </tr>
</table>

Composite action that runs the end-to-end Allure suite for each selected module.
For every module it writes an ephemeral `.env.<module>.<env-name>` file (0600,
removed via an `EXIT` trap) with the resolved service URLs and tenant
credentials, then runs `make test` scoped to `./cases/<module>/...` with its own
Allure result/report directories. Requires the end-to-end repo checked out and
Go / Node / Allure available.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `modules` | Comma-separated selected modules to run | Yes | — |
| `env-name` | Env-file suffix (`benedita-<base_env>-<tenancy>`) | Yes | — |
| `base-env` | Base environment (`dev`/`stg`/`prd`) for building URLs | Yes | — |
| `tenancy` | `st` or `mt` (`mt` sets `MULTI_TENANT=1`) | No | `st` |
| `service-domain` | Base domain — `https://<app>.<base-env>-<tenancy>.<service-domain>` | Yes | — |
| `auth-url` | Full `AUTH_URL` written to the env file | Yes | — |
| `timeout` | Per-run Go test timeout (`make test TIMEOUT=`) | No | `600s` |
| `admin-tenant-1-username` / `-password` | Tenant 1 login | No | `""` |
| `admin-tenant-2-username` / `-password` | Tenant 2 login (mt only) | No | `""` |

## Outputs

None. Allure reports are written to `reports/allure-report-<module>/`.

## Usage as composite step

```yaml
steps:
  - name: Run E2E suite
    uses: LerianStudio/github-actions-shared-workflows/src/e2e/run-suite@v1
    with:
      modules: ${{ steps.plan.outputs.modules }}
      env-name: ${{ steps.plan.outputs.env_name }}
      base-env: ${{ steps.plan.outputs.base_env }}
      tenancy: st
      service-domain: fuzzing.lerian.net
      auth-url: https://auth.${{ steps.plan.outputs.base_env }}-st.fuzzing.lerian.net
      admin-tenant-1-username: ${{ secrets.ADMIN_TENANT_1_USERNAME }}
      admin-tenant-1-password: ${{ secrets.ADMIN_TENANT_1_PASSWORD }}
```

## Usage via reusable workflow

Used internally by `end-to-end-tests.yml`.

## Required permissions

```yaml
permissions:
  contents: read
```
