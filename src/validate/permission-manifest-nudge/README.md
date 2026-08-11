<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>permission-manifest-nudge</h1></td>
  </tr>
</table>

**NON-BLOCKING** reminder that nudges a Go plugin/service to adopt the Access-Manager **Inversão de Responsabilidade (RI)** by declaring its permissions in a `permissions.yaml` manifest.

The action:

1. **Scope gate** — only acts when the repo looks like a plugin/service that *should* declare permissions, i.e. its `go.mod` has a **direct** dependency on `github.com/LerianStudio/lib-auth`. No `go.mod`, or no direct lib-auth dependency → it exits cleanly with no comment.
2. **Manifest presence** — globs every `permissions.yaml` (excluding `vendor/`, `node_modules/`, `.git/`) and keeps only files that look like a real declaration (top-level `service:` **and** `permissions:` keys).
3. **Sticky comment** — when in scope and no qualifying manifest exists, posts / updates a single find-by-marker PR comment inviting the team to adopt the RI. When a manifest *is* present it flips any prior nudge comment to a positive state (and never creates a new one).

> It **never fails**: every step is best-effort and exits 0. Pair it with `continue-on-error: true` on the calling job so a hiccup here can never gate a merge. It is **not** a required status check.

## Inputs

| Input           | Description                                                                                  | Required | Default                                                                       |
|-----------------|----------------------------------------------------------------------------------------------|----------|-------------------------------------------------------------------------------|
| `github-token`  | Token used to post / update the sticky PR comment. Needs `pull-requests:write` on the caller repo. | Yes      |                                                                               |
| `go-mod-path`   | Path to `go.mod` (relative to repo root). Used only for the lib-auth scope gate.             | No       | `go.mod`                                                                       |
| `guide-url`     | Link to the RI adoption guide surfaced in the nudge comment.                                 | No       | `https://alfarrabio.lerian.net/reports/brecci/declaracao-de-permissoes-v1-0`  |
| `comment-on-pr` | Post / update the sticky PR comment. When `false`, the check still runs but stays silent.    | No       | `true`                                                                         |

## Outputs

| Output         | Description                                                                        |
|----------------|------------------------------------------------------------------------------------|
| `applicable`   | `true` if the repo is in scope (go.mod depends on lib-auth); `false` = skipped.     |
| `has_manifest` | `true` if at least one qualifying `permissions.yaml` manifest was found.            |
| `state`        | `skip` (out of scope), `compliant` (manifest present), or `nudge` (in scope, none). |

## Behavior matrix

| Condition                                                    | Result                                                     |
|--------------------------------------------------------------|------------------------------------------------------------|
| `go.mod` not found at `go-mod-path`                          | `skip` — `::notice`, no comment, exit 0                     |
| `go.mod` has no **direct** `lib-auth` dependency             | `skip` — `::notice`, no comment, exit 0                    |
| In scope + a qualifying `permissions.yaml` exists            | `compliant` — flips an existing nudge comment to positive; creates nothing new |
| In scope + no qualifying `permissions.yaml`                  | `nudge` — posts / updates the single sticky reminder comment |
| Any internal / API error                                     | Logged as `::warning`; exit 0 (never fails)                |

## Scope gate — reviewer knob

The scope is deliberately narrow (direct lib-auth dep) to avoid noise on non-plugin repos. To tune it, edit the `grep` in `action.yml` step *Detect lib-auth scope and permission manifest*:

- drop the `// indirect` exclusion to also catch transitive lib-auth,
- match a different signal (e.g. `lib-commons`, a marker file, or a repo topic).

## Usage as composite step

```yaml
jobs:
  permission-manifest-nudge:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    continue-on-error: true   # non-blocking by contract
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v6
      - uses: LerianStudio/github-actions-shared-workflows/src/validate/permission-manifest-nudge@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

Most callers get this for free through the [`go-pr-validation`](../../../docs/go-pr-validation.md) umbrella (`run_manifest_nudge`, default `true`).

## Implementation notes

- Pure Bash + `actions/github-script` — no extra runtime required on the runner.
- The sticky comment is keyed by the HTML marker `<!-- permission-manifest-nudge -->`, so re-runs update the same comment instead of spamming per push.
- The manifest content check is intentionally light (`service:` + `permissions:` top-level keys) — it is a nudge, not a schema validator. `make validate-permissions` is the local validator teams run.
