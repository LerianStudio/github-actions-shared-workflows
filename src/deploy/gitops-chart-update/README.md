<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>gitops-chart-update</h1></td>
  </tr>
</table>

Pins a newly released Helm chart version into the GitOps repository.

The chart-version counterpart of the image-tag path owned by `gitops-update.yml`. Both read the same `config/deployment-matrix.yml`, so cluster topology — clusters, `env_contexts`, `env_suffixes`, `app_helmfile_env` — keeps a single source of truth.

Only releases whose `chart:` matches `chart-ref` **exactly** are touched. That is what stops an environment pinned to `oci://.../alpha/<chart>` from being overwritten with a stable-line version, which lives in a different OCI repository.

## Inputs

| Input | Description | Required | Default |
|---|---|---|---|
| `chart-name` | Chart name, also the key used in the deployment matrix | yes | — |
| `chart-version` | The version just published | yes | — |
| `chart-ref` | Full OCI reference; only this exact chart is touched | yes | — |
| `gitops-repository` | Target repo, validated against `^LerianStudio/<name>-gitops$` | yes | — |
| `gitops-token` | Token with write access to the GitOps repository | yes | — |
| `gpg-private-key` | CI GPG private key; the target ruleset requires signed commits | yes | — |
| `gpg-passphrase` | Passphrase for the CI GPG private key | yes | — |
| `git-user-name` | Committer name matching the CI GPG identity | yes | — |
| `git-user-email` | Committer email matching the CI GPG identity | yes | — |
| `deployment-matrix-ref` | Ref to read `config/deployment-matrix.yml` from | no | `main` |
| `migrations-path` | Migration directory inside the chart package; empty disables it | no | `migrations` |
| `target-envs` | Space-separated env list overriding the channel-derived one | no | `''` |
| `fail-on-orphan` | Fail when an environment sets a key the chart dropped | no | `true` |
| `dry-run` | Resolve, migrate and gate, then stop | no | `false` |

## Outputs

| Output | Description |
|---|---|
| `has-changes` | `true` when at least one pinned version changed |
| `level` | Most restrictive transition across every environment touched |
| `route` | How the change was delivered: `commit`, `pr` or `none` |

## Routing

The channel comes from the version suffix (`-beta.` → dev, `-rc.` → stg, clean → prd). Delivery then follows semver × environment, and because one bump spans several environments at once, the most restrictive cell wins:

| | dev | beyond dev |
|---|---|---|
| patch | commit | commit |
| minor | commit | **pull request** |
| major | **pull request** | **pull request** |

Environments drift apart, so the level is aggregated rather than read off one entry. `fetcher` currently sits at `3.1.0` in `dev-st` and `2.2.0-beta.2` in `prd-st`: a bump to `3.1.1` is `patch` in seven environments and `major` in production, and the aggregate is what routes.

## Gates

Both run before anything is delivered, and both run on a dry run too.

**Render** — `helmfile lint` and `helmfile template` on every changed file, against the mutated tree.

**Orphan keys** — a key set in an environment that no longer exists in the chart. This matters because the charts' `values.schema.json` is permissive (midaz has 106 `additionalProperties: true` against 2 `false`), so `helm template` accepts a key the chart dropped and the deploy silently falls back to the chart default — including for the image pin written by the image-tag path.

## Chart migrations

A chart can ship `migrations/<version>.yaml` describing what an upgrade does to consumer values:

```yaml
version: 9.0.0
ops:
  - { op: rename, from: .ledger.image.tag, to: .midaz.ledger.image.tag }
  - { op: remove, path: .tracer }
  - { op: require, path: .midaz.database.host }
```

`rename` and `remove` are applied to the environment values. `require` changes nothing and fails the run when the key is absent, because the new chart will not come up without it. Whoever broke the interface knows the mapping, so the migration travels with the chart.

## Usage as a composite step

```yaml
- name: Update the pinned chart version
  uses: LerianStudio/github-actions-shared-workflows/src/deploy/gitops-chart-update@v1.2.3
  with:
    chart-name: midaz
    chart-version: 9.1.0
    chart-ref: oci://ghcr.io/lerianstudio/midaz-helm
    gitops-repository: LerianStudio/lerian-internal-gitops
    gitops-token: ${{ steps.app-token.outputs.token }}
    gpg-private-key: ${{ secrets.LERIAN_CI_CD_USER_GPG_KEY }}
    gpg-passphrase: ${{ secrets.LERIAN_CI_CD_USER_GPG_KEY_PASSWORD }}
    git-user-name: ${{ secrets.LERIAN_CI_CD_USER_NAME }}
    git-user-email: ${{ secrets.LERIAN_CI_CD_USER_EMAIL }}
```

## Usage as a reusable workflow

```yaml
jobs:
  notify-gitops:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-chart-update.yml@v1.2.3
    with:
      chart_name: midaz
      chart_version: 9.1.0
      chart_ref: oci://ghcr.io/lerianstudio/midaz-helm
    secrets: inherit
```

## Required permissions

```yaml
permissions:
  contents: read
```

Write access to the GitOps repository comes from `gitops-token`, not from the job's `GITHUB_TOKEN`. The token is never persisted in the checkout: `helmfile` can execute release hooks against it, so credentials are supplied to git only at push time.
