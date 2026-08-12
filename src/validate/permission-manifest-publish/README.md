<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>permission-manifest-publish</h1></td>
  </tr>
</table>

Publishes a Go plugin/service's **own** permission manifest (`permissions.yaml`) to the shared Access-Manager **Inversão de Responsabilidade (RI)** catalog in S3, **on release**.

This is the **upstream half** of the RI: each service publishes exactly **one** object and the tenant-manager aggregates at **read time** by listing the prefix. There is **no merge / no aggregation** on write — one service overwrites only its own file. It is the release-time counterpart to [`permission-manifest-nudge`](../permission-manifest-nudge/README.md) (the PR reminder) and **reuses the same detection**, so the two always agree on what a manifest is.

The action:

1. **Scope gate** — identical to the nudge: only acts when `go.mod` has a **direct** dependency on `github.com/LerianStudio/lib-auth`. No `go.mod`, or an only-transitive (`// indirect`) dependency → `state=skip`.
2. **Manifest presence** — globs every `permissions.yaml` (excluding `vendor/`, `node_modules/`, `.git/`) and keeps only a file with top-level `service:` **and** `permissions:` keys. No qualifying manifest → `state=skip`.
3. **Service name** — extracts the manifest's top-level `service:` value; that is the **S3 object basename**.
4. **Publish** — `aws s3 cp <manifest> s3://<bucket>/<environment>/<prefix>/<service>.yaml --content-type application/yaml`. On `dry-run` it logs the exact target key + command and calls no AWS.

> **Best-effort by contract.** Every path exits 0; an upload hiccup logs `::warning` (not a failure). AWS credentials are assumed by the **caller** job (mirroring the `go-release` `s3_upload` job) before this composite runs. Pair it with `continue-on-error: true` on the calling job so a publish hiccup can never gate a release.

## S3 key layout

Per-service, env-scoped — one object per service:

```
s3://{s3-bucket}/{environment}/{s3-prefix}/{service}.yaml
# e.g. s3://lerian-casdoor-init-data/development/permissions/br-sisbajud.yaml
```

`{environment}` (`development` | `staging` | `production`) is passed in by the caller, derived from the tag suffix exactly like the S3 upload job (`-beta` → development, `-rc` → staging, `vX.Y.Z` → production). `{service}` is the manifest's `service:` value. The tenant-manager lists the `{environment}/{s3-prefix}/` prefix to aggregate every service's declaration.

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

| Output    | Description                                                                                  |
|-----------|----------------------------------------------------------------------------------------------|
| `state`   | `skip` (out of scope / no manifest / no environment / upload hiccup), `published` (uploaded), or `dryrun` (previewed). |
| `service` | The `service:` value extracted from the manifest — the S3 object basename (empty when skipped). |
| `s3_key`  | The full S3 object key it published (or would publish), e.g. `development/permissions/br-sisbajud.yaml`. |

## Behavior matrix

| Condition                                                     | Result                                                    |
|---------------------------------------------------------------|-----------------------------------------------------------|
| `go.mod` not found at `go-mod-path`                           | `skip` — `::notice`, no upload, exit 0                     |
| `go.mod` has no **direct** `lib-auth` dependency              | `skip` — `::notice`, no upload, exit 0                     |
| In scope + no qualifying `permissions.yaml`                   | `skip` — `::notice`, no upload, exit 0                     |
| Manifest has an empty `service:` value                        | `skip` — `::warning`, no upload, exit 0                    |
| `environment` empty (tag matched no env)                      | `skip` — `::warning`, no upload, exit 0                    |
| In scope + manifest + `dry-run: true`                         | `dryrun` — logs target key + command, no AWS call, exit 0  |
| In scope + manifest + real upload succeeds                    | `published` — `aws s3 cp`, `::notice` with the key, exit 0 |
| Upload fails (AWS hiccup)                                      | `skip` — `::warning`, exit 0 (never fails the release)     |

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
| `aws-actions/configure-aws-credentials` | Obtains short-lived OIDC credentials for the `aws s3 cp` upload, assuming the bucket-scoped `AWS_INIT_DATA_ROLE_ARN` role — no long-lived keys. Skipped on a dry-run (no AWS call) and when the role secret is unset. |

## Implementation notes

- Pure Bash + the AWS CLI (pre-installed on the runners). No extra runtime required.
- **Detection is copied verbatim from `permission-manifest-nudge`** (scope grep + `service:`/`permissions:` content check) so the nudge and the publisher never disagree on "what is a manifest". Keep them in sync if either changes.
- One object per service, keyed by `service:` — a rename of the service creates a **new** object; the old key is not garbage-collected here.
- Credentials are the caller's responsibility (as with the `s3_upload` job): the composite runs `aws s3 cp` against whatever role the caller assumed.
