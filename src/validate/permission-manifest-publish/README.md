<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>permission-manifest-publish</h1></td>
  </tr>
</table>

Publishes a Go plugin/service's **own** permission manifest (`permissions.yaml`) to the shared Access-Manager **Inversão de Responsabilidade (RI)** catalog in S3, **on release**.

This is the **upstream half** of the RI: each **service identity** publishes exactly **one** object and the tenant-manager aggregates at **read time** by listing the prefix. There is **no merge / no aggregation** on write — one service overwrites only its own file. It is the release-time counterpart to [`permission-manifest-nudge`](../permission-manifest-nudge/README.md) (the PR reminder) and **reuses the same detection**, so the two always agree on what a manifest is.

A repo may host **several** app identities. A monorepo like **midaz** ships four (`midaz`, `routing`, `plugin-fees`, `tracer`); `br-sfn` and `br-pix` are similar. Each qualifying `permissions.yaml` is published as its **own** S3 object keyed by its `service:` value — the action publishes **every** qualifying manifest, not just the first.

The action:

1. **Scope gate** — identical to the nudge: only acts when `go.mod` has a **direct** dependency on `github.com/LerianStudio/lib-auth`. No `go.mod`, or an only-transitive (`// indirect`) dependency → `state=skip`.
2. **Manifest presence** — globs **every** `permissions.yaml` (excluding `vendor/`, `node_modules/`, `.git/`) and **collects** each file with top-level `service:` **and** `permissions:` keys (results are `sort`ed for a deterministic first-published). No qualifying manifest → `state=skip`.
3. **Per-manifest publish** — for **each** collected manifest it extracts that manifest's own top-level `service:` value (the **S3 object basename**) and runs `aws s3 cp <manifest> s3://<bucket>/<environment>/<prefix>/<service>.yaml --content-type application/yaml`. On `dry-run` it logs the exact target key + command per manifest and calls no AWS.
4. **Anti-clobber guard** — if two manifests declare the **same** `service:` value they would resolve to the same S3 key and overwrite each other. That is a real repo error: the action logs a **loud `::warning`** naming the service and the offending file and **skips the duplicate** (the first one still publishes) rather than silently picking one. Consistent with the best-effort contract, this never fails the release.

> **Multiple identities, one object each.** A repo that hosts several app identities (like midaz) publishes one S3 object per `service:`.
>
> **Placement caveat.** Detection matches the **basename** `permissions.yaml` exactly, so each service's manifest must currently live in its **own directory** (e.g. `components/onboarding/permissions.yaml`, `components/transaction/permissions.yaml`). You **cannot** put `midaz.yaml` + `routing.yaml` side by side in one folder. Supporting multiple `service:` documents in a single multi-document YAML file is a possible **future** enhancement and is **not** implemented today.

> **Best-effort by contract.** Every path exits 0; an upload hiccup logs `::warning` (not a failure). AWS credentials are assumed by the **caller** job (mirroring the `go-release` `s3_upload` job) before this composite runs. Pair it with `continue-on-error: true` on the calling job so a publish hiccup can never gate a release.

## S3 key layout

Per-service, env-scoped — **one object per `service:` value**, and a repo publishes **N** of them (one per qualifying manifest):

```
s3://{s3-bucket}/{environment}/{s3-prefix}/{service}.yaml
# single-identity repo:
#   s3://lerian-casdoor-init-data/development/permissions/br-sisbajud.yaml
# multi-identity monorepo (midaz), one object each:
#   s3://lerian-casdoor-init-data/development/permissions/midaz.yaml
#   s3://lerian-casdoor-init-data/development/permissions/routing.yaml
#   s3://lerian-casdoor-init-data/development/permissions/plugin-fees.yaml
#   s3://lerian-casdoor-init-data/development/permissions/tracer.yaml
```

`{environment}` (`development` | `staging` | `production`) is passed in by the caller, derived from the tag suffix exactly like the S3 upload job (`-beta` → development, `-rc` → staging, `vX.Y.Z` → production). `{service}` is each manifest's `service:` value. The tenant-manager lists the `{environment}/{s3-prefix}/` prefix to aggregate every service's declaration. Because the key is derived from `service:` (not the file path), each service's manifest must live in its **own directory** — see the placement caveat above.

## Inputs

| Input          | Description                                                                                     | Required | Default                      |
|----------------|-------------------------------------------------------------------------------------------------|----------|------------------------------|
| `environment`  | Resolved environment folder (`development` \| `staging` \| `production`), derived by the caller from the tag suffix. Empty → `skip`. | Yes      |                              |
| `go-mod-path`  | Path to `go.mod` (relative to repo root). Used only for the lib-auth scope gate.               | No       | `go.mod`                     |
| `s3-bucket`    | Target S3 bucket (without the `s3://` prefix). Same bucket as the Casdoor `init_data`.          | No       | `lerian-casdoor-init-data`   |
| `s3-prefix`    | Prefix inside the environment folder — the key is `{environment}/{s3-prefix}/{service}.yaml`.   | No       | `permissions`                |
| `aws-region`   | AWS region for the `aws s3 cp` call.                                                             | No       | `us-east-2`                  |
| `github-token` | Optional. Reserved for future summary/annotation use; no PR side effects.                       | No       | `""`                         |
| `dry-run`      | Preview mode. When `true`, logs the exact target key and `aws s3 cp` command WITHOUT calling AWS. | No       | `false`                      |

## Outputs

| Output            | Description                                                                                  |
|-------------------|----------------------------------------------------------------------------------------------|
| `state`           | `skip` (out of scope / no manifest / no environment / nothing landed), `published` (≥1 uploaded), or `dryrun` (≥1 previewed). |
| `service`         | **Backward-compat.** The **first** published `service:` value — the S3 object basename (empty when skipped). See `services` for the full set. |
| `s3_key`          | **Backward-compat.** The **first** published S3 object key, e.g. `development/permissions/midaz.yaml` (empty when skipped). See `s3_keys` for the full set. |
| `services`        | Comma-separated list of **every** service published (or previewed), e.g. `midaz,routing,plugin-fees,tracer` (empty when skipped). |
| `s3_keys`         | Comma-separated list of **every** S3 object key published (or previewed), e.g. `development/permissions/midaz.yaml,development/permissions/routing.yaml` (empty when skipped). |
| `published_count` | How many manifests were published (or, on dry-run, previewed). `0` when skipped. |

> **Backward compatibility.** Existing consumers that read only `service` / `s3_key` keep working — those now carry the **first** published entry (the manifests are `sort`ed so "first" is deterministic). New consumers should prefer `services` / `s3_keys` / `published_count` to see the whole set.

## Behavior matrix

| Condition                                                     | Result                                                    |
|---------------------------------------------------------------|-----------------------------------------------------------|
| `go.mod` not found at `go-mod-path`                           | `skip` — `::notice`, no upload, exit 0                     |
| `go.mod` has no **direct** `lib-auth` dependency              | `skip` — `::notice`, no upload, exit 0                     |
| In scope + no qualifying `permissions.yaml`                   | `skip` — `::notice`, no upload, exit 0                     |
| `environment` empty (tag matched no env)                      | `skip` — `::warning`, no upload, exit 0 (short-circuits the whole action) |
| In scope + N manifests + `dry-run: true`                      | `dryrun` — logs one target key + command **per manifest**, no AWS call, exit 0 |
| In scope + N manifests + real uploads succeed                 | `published` — one `aws s3 cp` per manifest, `::notice` per key + a summary, `published_count=N`, exit 0 |
| A single manifest has an empty `service:` value               | that manifest is **skipped** (`::warning`); others still publish. All-empty → `skip` |
| Two manifests declare the **same** `service:`                 | duplicate **skipped** with a loud `::warning`; the first still publishes (anti-clobber) |
| One manifest's upload fails (AWS hiccup)                       | that manifest `::warning`, not counted; others still publish; all-fail → `skip` — exit 0 (never fails the release) |

## Usage as composite step

The **caller** assumes AWS credentials first (via OIDC), then invokes the composite:

```yaml
jobs:
  permission-manifest-publish:
    if: github.ref_type == 'tag'
    runs-on: blacksmith-4vcpu-ubuntu-2404
    continue-on-error: true      # non-blocking by contract
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v6
        with:
          persist-credentials: false

      # Derive the env folder from the tag suffix (beta→development, rc→staging, vX.Y.Z→production)
      # ... then assume the casdoor-init-data-scoped role:
      - uses: aws-actions/configure-aws-credentials@e7f100cf4c008499ea8adda475de1042d6975c7b # v6.2.0
        with:
          role-to-assume: ${{ secrets.AWS_INIT_DATA_ROLE_ARN }}
          aws-region: us-east-2

      - uses: LerianStudio/github-actions-shared-workflows/src/validate/permission-manifest-publish@v1
        with:
          environment: development   # resolved from the tag
```

Most callers get this for free through the [`go-release`](../../../docs/go-release-workflow.md) umbrella (`run_manifest_publish`, default `true`), which handles the checkout, tag→folder derivation and role-assume for you.

### Third-party actions

The composite itself uses none — it is pure Bash + the AWS CLI. The two external actions above belong to the **caller** and are pinned by full commit SHA:

| Action | Why |
|--------|-----|
| `actions/checkout` | Checks the repository out so the `permissions.yaml` manifest is present in the workspace for detection and upload. |
| `aws-actions/configure-aws-credentials` | Obtains short-lived OIDC credentials for the `aws s3 cp` upload, assuming the bucket-scoped `AWS_INIT_DATA_ROLE_ARN` role — no long-lived keys. In the [`go-release`](../../../docs/go-release-workflow.md) umbrella the credential step is guarded (`if: … dry_run != true && HAS_INIT_DATA_ROLE == 'true'`), so it is skipped on a dry-run and when the role secret is unset; a standalone caller (the minimal snippet above) must add the equivalent guard itself if it wants that skip behaviour. |

## Implementation notes

- Pure Bash + the AWS CLI (pre-installed on the runners). No extra runtime required.
- **Detection is copied verbatim from `permission-manifest-nudge`** (scope grep + `service:`/`permissions:` content check) so the nudge and the publisher never disagree on "what is a manifest". Keep them in sync if either changes. (The nudge only needs a yes/no answer so it stops at the first match; the publisher **collects them all**, but the qualifying grep is identical.)
- **One object per `service:`, N per repo** — the action iterates over every qualifying manifest. A rename of a service creates a **new** object; the old key is not garbage-collected here. Two manifests with the same `service:` collide and the duplicate is skipped with a `::warning`.
- **Placement**: matching is on the basename `permissions.yaml`, so co-locating two services' manifests in one directory is not supported today — give each service its own directory. A single multi-document YAML per repo is a possible future enhancement (not implemented).
- Credentials are the caller's responsibility (as with the `s3_upload` job): the composite runs `aws s3 cp` against whatever role the caller assumed.
- **Tests**: `test.py` (Python `unittest`, run in CI by `self-pr-validation.yml`) extracts the embedded `run:` block and exercises it in throwaway workspaces via dry-run (and a stubbed `aws` for the real success/failure branches): multi-manifest publish, duplicate-service collision, single manifest, and the skip cases.
