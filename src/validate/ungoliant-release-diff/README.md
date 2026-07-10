<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>ungoliant-release-diff</h1></td>
  </tr>
</table>

Resolves a release diff and fires the `release-diff` webhook at the Ungoliant controller to trigger chaos/fuzz analysis for a release tag.

This is the CI equivalent of `ungoliant-controller/docs/testing/cluster/test-release.sh`. The action:

1. Resolves the target repository as `<repo-owner>/<app>` and composes `target_env = <testing-type>-<base-env>-<tenancy>`.
2. Auto-resolves the previous tag from the GitHub API when `previous` is empty.
3. Fetches the `previous...version` compare (revision SHA, previous SHA, files changed) and the raw diff, capped at `max-diff-bytes`.
4. Builds the JSON payload (`app, env, repository, version, revision, previous, diff, target_env`).
5. Health-checks the controller `/healthz`.
6. POSTs the payload to `/webhook/release-diff` with the `X-Ungoliant-Token` header and reports the analysis result.

> The controller is only reachable over Tailscale, so the job must run on a Tailscale-connected self-hosted runner (e.g. `eveo-anacleto-lxc-runners`).

## Inputs

| Input            | Description                                                                     | Required | Default                                              |
|------------------|---------------------------------------------------------------------------------|----------|------------------------------------------------------|
| `app`            | App slug (midaz, reporter, plugin-fees, …).                                     | Yes      |                                                      |
| `version`        | Tag to test (e.g. `v1.3.4-beta.1`).                                             | Yes      |                                                      |
| `previous`       | Previous tag for the diff. Auto-resolved from the GitHub API when empty.        | No       | `""`                                                 |
| `env`            | Release channel — `beta` \| `rc` \| `stable`.                                   | No       | `beta`                                               |
| `testing-type`   | Testing type — `chaos` \| `fuzzing`. Empty produces a legacy `target_env`.      | No       | `chaos`                                              |
| `tenancy`        | Tenancy — `st` (single-tenant) \| `mt` (multi-tenant).                          | No       | `st`                                                 |
| `base-env`       | Base environment — `dev` \| `stg` \| `prd`.                                     | No       | `dev`                                                |
| `controller-url` | Ungoliant controller base URL (reachable over Tailscale).                       | No       | `https://ungoliant-controller.anacleto.lerian.net`   |
| `repo-owner`     | GitHub owner/org that hosts the app repository.                                 | No       | `LerianStudio`                                       |
| `github-token`   | GitHub token used to read tags, compare and diff via the API.                   | Yes      |                                                      |
| `webhook-token`  | Ungoliant webhook token sent as the `X-Ungoliant-Token` header.                 | No       | `""`                                                 |
| `max-diff-bytes` | Maximum diff size forwarded to the controller (bytes).                          | No       | `262144`                                             |
| `curl-timeout`   | Timeout for the webhook POST in seconds.                                         | No       | `300`                                                |
| `dry-run`        | Resolve and preview the payload without firing the webhook.                     | No       | `false`                                              |

## Outputs

| Output       | Description                                              |
|--------------|----------------------------------------------------------|
| `status`     | Controller response status (e.g. `analysis_completed`).  |
| `run-id`     | Controller `run_id` for the analysis.                    |
| `schema`     | Response schema (`release-plan` \| `release-summary`).   |
| `risk-level` | Risk level reported by the controller.                   |
| `target-env` | Composed `target_env` forwarded to the controller.       |

## Usage as composite step

```yaml
jobs:
  release-diff:
    runs-on: eveo-anacleto-lxc-runners
    permissions:
      contents: read
    steps:
      - name: Send release-diff webhook
        uses: LerianStudio/github-actions-shared-workflows/src/validate/ungoliant-release-diff@develop
        with:
          app: reporter
          version: ${{ github.ref_name }}
          env: beta
          github-token: ${{ secrets.GITHUB_TOKEN }}
          webhook-token: ${{ secrets.UNGOLIANT_WEBHOOK_TOKEN }}
```

## Usage as reusable workflow

Prefer the reusable workflow for a one-line integration:

```yaml
jobs:
  release-diff:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/ungoliant-release-diff.yml@develop
    with:
      app: reporter
      version: ${{ github.ref_name }}
    secrets: inherit
```

## Required permissions

```yaml
permissions:
  contents: read   # read tags / compare / diff via the GitHub API
```

## Implementation notes

- Pure Bash + `curl` + `jq` — no `gh` CLI or Python runtime is required on the runner.
- The diff is streamed to the controller via `--data-binary @payload.json`, avoiding the per-argument length limit (`E2BIG`) that a large diff hits when passed as an argv value.
- The byte-level diff cap is UTF-8-sanitised with `iconv -c` so a truncated multi-byte sequence never breaks the JSON payload.
- A `analysis_completed` status is required for the step to succeed; any other status fails the job.
