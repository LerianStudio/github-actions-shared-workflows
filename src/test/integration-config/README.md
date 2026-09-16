<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>integration-config</h1></td>
  </tr>
</table>

Parses the `integration_tests_config` JSON used by `go-pr-analysis.yml`, validates it, exports its `test_env` entries to the job environment, and exposes the `service` and `guard` settings as step outputs.

`workflow_call` inputs can only be `string`, `number` or `boolean` — there is no `type: object` — so a grouped configuration has to travel as a JSON string. That trades the Actions-level schema check for silence on a typo, which is the wrong failure for a feature whose entire purpose is to stop CI reporting coverage it never produced. This action buys that check back: **any unrecognised key is a hard error**, not a dropped setting.

## Schema

```jsonc
{
  "service": {                       // optional — a backing container on the runner
    "image": "postgres:16.13",       // required when `service` is present
    "ports": "5432:5432",            // string or array of "host:container"
    "health_cmd": "pg_isready",      // run inside the container until it exits 0
    "health_timeout": 60,            // seconds, default 60
    "env": { "POSTGRES_PASSWORD": "postgres" }
  },
  "test_env": {                      // optional — exported to the job environment
    "POSTGRES_TEST_URL": "postgres://…"
  },
  "guard": {                         // optional — anti-skip guard
    "packages": "./internal/store/ ./internal/httpapi/",
    "pattern": "AgainstRealPostgres"
  }
}
```

Validation performed:

| Rule | Outcome |
|---|---|
| Unknown key at any level | error |
| `service.image` missing while `service` is present | error |
| `service.image` without a tag | warning — a floating tag makes "CI matches production" quietly untrue |
| `service.health_cmd` empty | warning — the first connection then races the container's startup |
| `service.ports` entry not `host:container` | error |
| `service.env` / `test_env` value not a scalar | error |
| `service.env` / `test_env` key not a shell identifier, or using a `GITHUB_`/`ACTIONS_`/`RUNNER_` prefix | error |
| `guard.packages` or `guard.pattern` missing while `guard` is present | error |
| `guard.packages` entry or `guard.pattern` starting with `-` | error — `go test` would read it as a flag |

## Inputs

| Input | Description | Required | Default |
|---|---|---|---|
| `config` | The `integration_tests_config` JSON object | Yes | — |

## Outputs

| Output | Description |
|---|---|
| `has-service` | `"true"` when a service container is configured |
| `service-image` | Container image |
| `service-ports` | Space-separated `host:container` mappings |
| `service-health-cmd` | Health command |
| `service-health-timeout` | Health timeout in seconds |
| `service-env-json` | JSON object of container environment variables |
| `has-guard` | `"true"` when the guard is configured |
| `guard-packages` | Space-separated packages |
| `guard-pattern` | Test-name pattern |

`test_env` has no output: its entries are written straight to `$GITHUB_ENV`, and the log records the names only — the values are typically connection strings carrying credentials.

## Usage as composite step

```yaml
- name: Parse integration configuration
  id: integration-config
  if: inputs.integration_tests_config != ''
  uses: LerianStudio/github-actions-shared-workflows/src/test/integration-config@v1
  with:
    config: ${{ inputs.integration_tests_config }}

- name: Start service container
  if: steps.integration-config.outputs.has-service == 'true'
  uses: LerianStudio/github-actions-shared-workflows/src/test/service-container@v1
  with:
    name: integration-svc-${{ github.run_id }}
    image: ${{ steps.integration-config.outputs.service-image }}
    ports: ${{ steps.integration-config.outputs.service-ports }}
    env-json: ${{ steps.integration-config.outputs.service-env-json }}
    health-cmd: ${{ steps.integration-config.outputs.service-health-cmd }}
```

Gate the following steps on `steps.integration-config.outputs.has-service`, never on `fromJSON(inputs.integration_tests_config).service` — `fromJSON('')` errors when the input is empty.

## Usage as reusable workflow

Callers do not use this action directly. It is wired into `go-pr-analysis.yml`, reached through `go-pr-validation.yml`:

```yaml
jobs:
  validate:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-pr-validation.yml@v1.72.0
    with:
      enable_integration_tests: true
      integration_tests_config: |
        { "service": { "image": "postgres:16.13", "ports": "5432:5432", "health_cmd": "pg_isready",
                       "env": { "POSTGRES_PASSWORD": "postgres", "POSTGRES_DB": "app" } },
          "test_env": { "POSTGRES_TEST_URL": "postgres://postgres:postgres@127.0.0.1:5432/app?sslmode=disable" },
          "guard": { "packages": "./internal/store/", "pattern": "AgainstRealPostgres" } }
    secrets: inherit
```

## Required permissions

None. The action only reads its input and writes to `$GITHUB_ENV` / `$GITHUB_OUTPUT`.
