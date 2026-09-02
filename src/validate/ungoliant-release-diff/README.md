<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>ungoliant-release-diff</h1></td>
  </tr>
</table>

Resolves a release diff and fires the `release-diff` webhook at the Ungoliant controller to trigger chaos/fuzz analysis for a release tag.

This is the CI equivalent of `ungoliant-controller/docs/testing/cluster/test-release.sh`. The action:

1. Resolves the target repository as `<repo-owner>/<app>`.
2. Auto-resolves the previous tag from the GitHub API when `previous` is empty.
3. Fetches the `previous...version` compare metadata (revision SHA, previous SHA, changed files) and checks every changed file against `skip-globs`. When all of them match, the release is CI/meta-only: the controller is **never contacted** — no health check, no diff fetch, no webhook call — and the action reports `outcome: skipped_ci_only`.
4. Otherwise: health-checks the controller `/healthz`, fetches the raw diff (capped at `max-diff-bytes`), builds the JSON payload (`app, env, repository, version, revision, previous, diff`), and POSTs it to `/webhook/release-diff` with the `X-Ungoliant-Token` header, reporting the analysis result.

> The controller is only reachable over Tailscale, so the job must run on a Tailscale-connected self-hosted runner (e.g. `eveo-anacleto-lxc-runners`).

## Where a release is validated

**The application's registration decides, not this action.** The `env` channel picks the cluster (`beta`→dev, `rc`→stg, `stable`→prd) and the tenancy registered in the console's Applications tab picks the rest.

The controller honours a `target_env` in the payload **over** its own configuration — a transitional path for callers that predate the Applications tab. This action used to compose one from `env-type`/`base-env`/`tenancy` and always send it, and since those inputs default to `chaos`/`dev`/`st`, *every* release silently overrode its own registration: an app registered for stg ran against dev without a word.

So `target_env` is no longer sent. `env-type`, `tenancy` and `base-env` are kept for compatibility but are **no-ops** unless `send-target-env: true`, which restores the override and emits a warning naming what it outranks.

An application with no registration for the channel is **refused** when the controller runs with `UNGOLIANT_REQUIRE_REGISTRATION` on. That refusal is the configuration doing its job; it surfaces here as a failed outcome rather than being papered over.

## Inputs

| Input            | Description                                                                     | Required | Default                                              |
|------------------|---------------------------------------------------------------------------------|----------|------------------------------------------------------|
| `app`            | App slug (midaz, reporter, plugin-fees, …).                                     | Yes      |                                                      |
| `version`        | Tag to test (e.g. `v1.3.4-beta.1`).                                             | Yes      |                                                      |
| `previous`       | Previous tag for the diff. Auto-resolved from the GitHub API when empty.        | No       | `""`                                                 |
| `env`            | Release channel — `beta` \| `rc` \| `stable`.                                   | No       | `beta`                                               |
| `env-type`       | **Deprecated, no-op** unless `send-target-env` is true — `chaos` \| `fuzzing`.  | No       | `chaos`                                              |
| `tenancy`        | **Deprecated, no-op** unless `send-target-env` is true — `st` \| `mt`.          | No       | `st`                                                 |
| `base-env`       | **Deprecated, no-op** unless `send-target-env` is true — `dev` \| `stg` \| `prd`. | No     | `dev`                                                |
| `send-target-env`| Send the composed `target_env`, overriding the app's registration. See [Where a release is validated](#where-a-release-is-validated). | No | `false` |
| `controller-url` | Ungoliant controller base URL (reachable over Tailscale).                       | No       | `https://ungoliant-controller.anacleto.lerian.net`   |
| `repo-owner`     | GitHub owner/org that hosts the app repository.                                 | No       | `LerianStudio`                                       |
| `github-token`   | GitHub token used to read tags, compare and diff via the API.                   | Yes      |                                                      |
| `webhook-token`  | Ungoliant webhook token sent as the `X-Ungoliant-Token` header.                 | No       | `""`                                                 |
| `max-diff-bytes` | Maximum diff size forwarded to the controller (bytes).                          | No       | `262144`                                             |
| `skip-globs`     | Space-separated glob patterns. When every changed file matches one, the release is CI/meta-only and the controller is never contacted. Empty disables the check. | No | `.releaserc.yml .github/*` |
| `curl-timeout`   | Timeout for the webhook POST in seconds. This is the **outermost** budget in the chain, so it must be **strictly larger** than every hop it fronts: bridge 780s < controller `NEMOCLAW_TIMEOUT_SECONDS` 900s < NPM edge and k8s ingress 960s < this 1020s. Equal is a race, not a safeguard — see [Timeout budget](#timeout-budget). | No | `1020` |
| `dry-run`        | Resolve and preview the payload without firing the webhook.                     | No       | `false`                                              |

## Outputs

| Output       | Description                                              |
|--------------|----------------------------------------------------------|
| `status`     | Controller response status (e.g. `analysis_completed`).  |
| `run-id`     | Controller `run_id` for the analysis.                    |
| `schema`     | Response schema (`release-plan` \| `release-summary`).   |
| `risk-level` | Risk level reported by the controller.                   |
| `target-env` | Composed `target_env`. Informational unless `send-target-env` is true, in which case it is what was forwarded. |
| `will-run`   | Space-separated test types the controller says it will run (populated when `status` is `accepted`). |
| `outcome`    | See the outcome table below.                             |
| `k6`         | Number of k6 smoke scenarios selected.                   |
| `chaos`      | Number of chaos experiments selected.                    |

### Outcomes

Not every status other than `analysis_completed` is a failure. This step used to
treat them all as one, so a channel configured for the authored suite alone —
doing exactly what it was configured to do — was reported as a broken release.

| Controller status | `outcome` | Step result |
|---|---|---|
| `analysis_completed`, k6 or chaos > 0 | `executed` | ✅ the full flow ran |
| `analysis_completed`, k6 and chaos both 0 | `skipped` | ✅ analysis ran, judged low-risk / provably trivial, no tests warranted |
| `accepted` | `accepted` | ✅ delivered; no agentic analysis requested for this channel. `will-run` names what runs instead — an authored suite runs detached, under its own `run_id` |
| `no_applicable_stages` | `no_stages` | ✅ with a loud `::warning` — delivered, but no test type is enabled for this app on this channel, so **the release validates nothing**. A configuration gap in the Applications tab, not a broken release |
| (never contacted, diff matched `skip-globs`) | `skipped_ci_only` | ✅ no health check, no webhook call |
| `analysis_failed`, a registration refusal, or an empty/unparseable body | `failed` | ❌ |

An empty body is usually a client-side timeout: when the reported elapsed time
equals `curl-timeout`, curl gave up before the controller answered, and the
error says so rather than blaming the app.

For non-dry-run invocations, every passing outcome also posts (or updates) a
comment on the pull request that produced the release, so reviewers see whether
the full flow ran, was skipped by the controller, was accepted without analysis,
validated nothing, or was never triggered because the change was CI/meta-only.
`dry-run: true` skips this comment entirely, along with the webhook call.
Posting the comment requires the calling job to grant `pull-requests: write`;
it is best-effort and never fails the release.

## Timeout budget

```
bridge 780s  <  controller 900s  <  edge/ingress 960s  <  curl-timeout 1020s
```

Each hop must **strictly** outlast what it fronts, so the innermost one gives up first and the failure is attributable to it. Equality is not lockstep, it is a coin toss: when `curl --max-time` and the budget it fronts expire together, whichever fires first decides whether you get a parseable error or an empty body naming nothing.

That is not hypothetical. A release analysis ran 899s against a 900s `curl --max-time` and the controller logged `context canceled` — the caller hanging up, indistinguishable from a proxy timeout without checking every hop. The `midaz` run [`33638307722`](https://github.com/LerianStudio/midaz/actions/runs/33638307722) hit the same tie and reported `Elapsed: 900s` with an empty status.

`1020` keeps the 60s spacing the rest of the chain already uses. The cost of raising the outermost budget is bounded and one-directional: a genuinely hung run occupies the release job longer, but a larger client timeout cannot fail a request that would otherwise have succeeded.

## Tests

```bash
python3 src/validate/ungoliant-release-diff/test.py
```

Runs the composite's own extracted payload and verdict steps against fixtures: the
payload with and without `send-target-env`, every documented controller status, and
the channel inference in `go-release.yml` / `js-release.yml` (including the tag
shapes that must be refused rather than guessed at). Hermetic — `curl` is stubbed,
so no controller and no network are needed. Requires bash 4+.

## Usage as composite step

```yaml
jobs:
  release-diff:
    runs-on: eveo-anacleto-lxc-runners
    permissions:
      contents: read          # read tags / compare / diff via the GitHub API
      pull-requests: write    # optional: post/update the outcome comment on the originating PR
    steps:
      - name: Send release-diff webhook
        uses: LerianStudio/github-actions-shared-workflows/src/validate/ungoliant-release-diff@v1
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
  contents: read          # read tags / compare / diff via the GitHub API
  pull-requests: write    # optional: post/update the outcome comment on the originating PR
```

## Implementation notes

- Pure Bash + `curl` + `jq` — no `gh` CLI or Python runtime is required on the runner.
- The `skip-globs` check runs first, off a cheap JSON-only compare (no diff body), so a CI-only release never triggers the health check or the heavier diff fetch.
- The diff is streamed to the controller via `--data-binary @payload.json`, avoiding the per-argument length limit (`E2BIG`) that a large diff hits when passed as an argv value.
- The byte-level diff cap is UTF-8-sanitised with `iconv -c` so a truncated multi-byte sequence never breaks the JSON payload.
- A `analysis_completed` status is required for the step to succeed; any other status fails the job.
