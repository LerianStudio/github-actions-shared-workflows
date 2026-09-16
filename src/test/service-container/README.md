<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>service-container</h1></td>
  </tr>
</table>

Starts a backing service — database, broker, cache — as a Docker container on the runner and blocks until its health command succeeds.

## Why not a `services:` block

`services.<id>.env` is a **static mapping**. It cannot be expanded from an input, so a shared workflow built on `services:` would have to hardcode every consumer's container variables. A `services:` block also cannot be declared conditionally, and `image:` resolving to an empty string fails the job — which is why the usual workaround is duplicating the whole job behind an `if:`.

`docker run` avoids both: the configuration stays entirely in the caller's hands, and one job covers the service and serviceless cases. The job runs on the runner itself rather than inside a container, so `--publish` puts the service on `localhost:<port>` exactly as `services:` would.

What you give up, and how it is covered here: the runner's automatic service logs (the caller's teardown step runs `docker logs`) and the Docker-native `--health-*` handling (replaced by the health loop below, which also fails immediately if the container exits rather than burning the full timeout).

## Inputs

| Input | Description | Required | Default |
|---|---|---|---|
| `name` | Container name — must be unique per concurrent job on the runner | Yes | — |
| `image` | Image reference. Pin to a patch version, not a floating minor | Yes | — |
| `ports` | Space-separated `host:container` port mappings | No | `""` |
| `env-json` | JSON object of environment variables for the container | No | `"{}"` |
| `health-cmd` | Command run inside the container until it exits 0. Empty means no wait | No | `""` |
| `health-timeout` | Seconds to wait for the health command before failing | No | `"60"` |

Values from `env-json` are assembled into a `docker run` argument array and never echoed — they are the container's credentials.

## Usage as composite step

```yaml
- name: Start service container
  uses: LerianStudio/github-actions-shared-workflows/src/test/service-container@v1
  with:
    name: integration-svc-${{ github.run_id }}-${{ strategy.job-index }}
    image: postgres:16.13
    ports: "5432:5432"
    env-json: '{"POSTGRES_PASSWORD":"postgres","POSTGRES_DB":"app"}'
    health-cmd: pg_isready
    health-timeout: "60"

# … run the suite …

- name: Stop service container
  if: always()
  env:
    NAME: integration-svc-${{ github.run_id }}-${{ strategy.job-index }}
  run: |
    echo "::group::Service container logs"
    docker logs "$NAME" 2>&1 | tail -n 200 || true
    echo "::endgroup::"
    docker rm --force "$NAME" > /dev/null 2>&1 || true
```

Two things the caller owns:

- **Teardown under `if: always()`.** Runners can be persistent, so a failed suite must not leave a container holding the port for the next job.
- **A name unique per concurrent job**, as above — otherwise two matrix legs on the same runner collide.

Pin the image to a patch version. `postgres:16` is mutable and silently becomes 16.14, 16.15…, so "CI matches the deployed planner" quietly stops being true — and a planner difference that passes CI and fails in the cluster is exactly what an integration suite exists to catch.

## Usage as reusable workflow

Reached through `go-pr-analysis.yml` via the `integration_tests_config.service` object — see [docs/go-pr-analysis.md](../../../docs/go-pr-analysis.md).

```yaml
jobs:
  validate:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-pr-validation.yml@v1.72.0
    with:
      enable_integration_tests: true
      integration_tests_config: |
        { "service": { "image": "postgres:16.13", "ports": "5432:5432",
                       "health_cmd": "pg_isready",
                       "env": { "POSTGRES_PASSWORD": "postgres", "POSTGRES_DB": "app" } } }
    secrets: inherit
```

## Required permissions

None. Requires a runner with a working Docker daemon.
