<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>ungoliant-release-diff</h1></td>
  </tr>
</table>

Reusable workflow that fires the `release-diff` webhook at the Ungoliant controller to trigger chaos/fuzz analysis for a release tag. It is the CI equivalent of `ungoliant-controller/docs/testing/cluster/test-release.sh`.

## Why

When a release tag is published, we want the Ungoliant controller to analyse the diff and produce a chaos/fuzz test plan for the change. Doing this by hand with `test-release.sh` requires a local machine on Tailscale, the `gh` CLI, and a webhook token. This workflow turns that manual step into an automated post-release job.

## Architecture

```
ungoliant-release-diff.yml (reusable workflow)
   ↓ runs on eveo-anacleto-lxc-runners (Tailscale-connected)
src/validate/ungoliant-release-diff (composite action)
   ↓
   1. Resolve repo = <repo-owner>/<app> and target_env = <testing-type>-<base-env>-<tenancy>
   2. Auto-resolve the previous tag (GitHub API) when not provided
   3. Fetch compare (revision SHA, previous SHA, files) + raw diff (capped)
   4. Build JSON payload (app, env, repository, version, revision, previous, diff, target_env)
   5. Health check the controller /healthz
   6. POST /webhook/release-diff with X-Ungoliant-Token
   7. Parse the response and fail unless status == analysis_completed
```

> The controller is only reachable over Tailscale. The job defaults to the `eveo-anacleto-lxc-runners` self-hosted runner, which is already on the Tailscale network — no connect step is required.

## Usage

### Automatic on release tag

```yaml
name: Ungoliant Release Diff

on:
  push:
    tags:
      - 'v2.0.*'

permissions:
  contents: read

jobs:
  release-diff:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/ungoliant-release-diff.yml@v1.x.x
    with:
      app: reporter
      version: ${{ github.ref_name }}
      env: ${{ contains(github.ref_name, '-beta.') && 'beta' || (contains(github.ref_name, '-rc.') && 'rc' || 'stable') }}
      testing_type: chaos
      tenancy: st
      base_env: dev
    secrets: inherit
```

### Multi-tenant / staging target

```yaml
jobs:
  release-diff:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/ungoliant-release-diff.yml@v1.x.x
    with:
      app: midaz
      version: ${{ github.ref_name }}
      testing_type: chaos
      tenancy: mt
      base_env: stg
    secrets: inherit
```

### Dry run (preview without firing)

```yaml
jobs:
  release-diff:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/ungoliant-release-diff.yml@v1.x.x
    with:
      app: reporter
      version: ${{ github.ref_name }}
      dry_run: true
    secrets: inherit
```

## Inputs

| Name             | Type    | Default                                              | Description                                                                 |
|------------------|---------|------------------------------------------------------|-----------------------------------------------------------------------------|
| `app`            | string  | —                                                    | App slug (midaz, reporter, plugin-fees, …). **Required.**                   |
| `version`        | string  | —                                                    | Tag to test (e.g. `v1.3.4-beta.1`). **Required.**                           |
| `previous`       | string  | `''`                                                 | Previous tag for the diff. Auto-resolved when empty.                        |
| `env`            | string  | `beta`                                               | Release channel — `beta` \| `rc` \| `stable`.                               |
| `testing_type`   | string  | `chaos`                                              | Testing type — `chaos` \| `fuzzing`.                                        |
| `tenancy`        | string  | `st`                                                 | Tenancy — `st` (single-tenant) \| `mt` (multi-tenant).                      |
| `base_env`       | string  | `dev`                                                | Base environment — `dev` \| `stg` \| `prd`.                                 |
| `controller_url` | string  | `https://ungoliant-controller.anacleto.lerian.net`   | Ungoliant controller base URL.                                              |
| `repo_owner`     | string  | `LerianStudio`                                       | GitHub owner/org that hosts the app repository.                             |
| `max_diff_bytes` | string  | `262144`                                             | Maximum diff size forwarded to the controller (bytes).                      |
| `curl_timeout`   | string  | `300`                                                | Timeout for the webhook POST in seconds.                                    |
| `runner_type`    | string  | `eveo-anacleto-lxc-runners`                          | Runner label. Needs Tailscale reach to the controller.                     |
| `dry_run`        | boolean | `false`                                              | Resolve and preview the payload without firing the webhook.                 |

## Secrets

| Name                      | Required | Description                                                       |
|---------------------------|----------|-------------------------------------------------------------------|
| `UNGOLIANT_WEBHOOK_TOKEN` | No       | Sent as the `X-Ungoliant-Token` header. Unauthenticated when unset. |

The workflow uses the automatic `GITHUB_TOKEN` to read tags, compare, and diff via the GitHub API.

## Outputs

| Name         | Description                                              |
|--------------|----------------------------------------------------------|
| `status`     | Controller response status (e.g. `analysis_completed`).  |
| `run_id`     | Controller `run_id` for the analysis.                    |
| `schema`     | Response schema (`release-plan` \| `release-summary`).   |
| `risk_level` | Risk level reported by the controller.                   |

## Required permissions

```yaml
permissions:
  contents: read
```

## Failure modes

| Condition                                       | Behavior                                        |
|-------------------------------------------------|-------------------------------------------------|
| `app` or `version` empty                        | Fail with `::error`                             |
| `testing_type` not `chaos`/`fuzzing`            | Fail with `::error`                             |
| `tenancy` not `st`/`mt`                         | Fail with `::error`                             |
| Previous tag cannot be resolved                 | Fail — pass `previous` explicitly               |
| Empty diff (tags missing)                       | Fail with `::error`                             |
| Controller `/healthz` not `200`                 | Fail — runner not on Tailscale?                 |
| Response status != `analysis_completed`         | Fail — analysis did not complete                |
| `dry_run: true`                                 | Preview only, webhook not sent                  |

## Notes

- Pure Bash + `curl` + `jq` — no `gh` CLI or Python runtime is required on the runner.
- The diff is streamed via `--data-binary @payload.json`, avoiding the `E2BIG` argv-length limit that a large diff hits when passed as a value.
- The byte-level diff cap is UTF-8-sanitised with `iconv -c` so a truncated multi-byte sequence never breaks the JSON payload.
