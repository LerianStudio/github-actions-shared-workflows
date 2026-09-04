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
| `target-envs` | Space-separated env list overriding the channel-derived one | no | `''` |
| `fail-on-orphan` | Fail when an environment sets a key the chart dropped | no | `true` |
| `dry-run` | Resolve and run both gates, then stop | no | `false` |
| `enable-argocd-sync` | Sync the affected applications and wait for healthy after a direct commit | no | `true` |
| `argocd-url` | ArgoCD server; required when the sync is enabled | no | `''` |
| `argocd-token` | ArgoCD auth token; required when the sync is enabled | no | `''` |
| `argocd-sync-timeout` | Seconds to wait for each application to become healthy | no | `600` |

## Outputs

| Output | Description |
|---|---|
| `has-changes` | `true` when at least one pinned version changed |
| `level` | Most restrictive transition across every environment touched |
| `route` | How the change was delivered: `commit`, `pr` or `none` |
| `synced` | `true` when every affected ArgoCD application reported healthy |

## Reconciliation

Writing to git is not the same as the change being live. After a **direct commit** the composite syncs each affected ArgoCD application and waits for it to report healthy; a run that cannot reach that state fails instead of reporting success over a half-updated cluster.

The application name is derived from the changed path — `environments/<cluster>/helmfile/applications/<env>/<app>/` becomes `<cluster>-<app>-<env>`, with the context separator flattened, so `chaos/dev-st` gives `anacleto-midaz-chaos-dev-st`.

It does not run on the pull-request route, because nothing has been applied yet, and it does not run on a dry run.

**Turning it off.** `enable-argocd-sync: false` writes to git and lets ArgoCD reconcile on its own schedule. Reasonable when the target application has automated sync with a short interval, or when the caller wants the pipeline to finish without waiting on cluster health.

**No automatic rollback.** A failed sync leaves the commit on `main` and fails loudly with the application name. Reverting automatically would undo a good change whenever the ArgoCD API is briefly unavailable, so the choice between rolling back and fixing forward stays with a person.

## Routing

### Which environments a release reaches

The channel comes from the version suffix:

| Tag | Environments |
|---|---|
| `-beta.N` | `dev` |
| `-rc.N` | `stg` |
| clean | `dev`, `stg`, `prd` |

A clean tag walking the whole ladder is deliberate and differs from the image-tag path, where stable means `prd` alone. The chart repositories release from `main` only, so every chart tag is stable; mapping it to `prd` would mean no chart ever reaches `dev` or `stg`, and production would receive charts that had run nowhere else.

`beta` and `rc` stay declared and inert. They cost nothing, and if a chart repository starts releasing prereleases again the behaviour is already right instead of quietly sending one to production.

Anacleto is included automatically. Its `env_contexts` expand `dev` into `chaos/dev-st` and `fuzzing/dev-st`, so a single stable release of `midaz` today resolves six targets: those two plus benedita's `dev-st`, `stg-st`, `stg-mt` and `prd-st`.

### How it is delivered

| Level | Route |
|---|---|
| patch | commit |
| minor | commit |
| major | **pull request** |

Only a major waits for a person. A chart release is one change, and reviewing the same minor once per environment adds nothing — the level is already the most restrictive transition across every environment touched, so a `minor` here means no environment saw a larger jump.

Environments drift apart, so the level is aggregated rather than read off one entry. `fetcher` currently sits at `3.1.0` in `dev-st` and `2.2.0-beta.2` in `prd-st`: a bump to `3.1.1` is `patch` in seven environments and `major` in production, and the aggregate is what routes.

## Gates

Both run before anything is delivered, and both run on a dry run too. **They detect and stop — they never repair.**

**Render** — `helmfile lint` and `helmfile template` on every changed file, against the mutated tree.

**Orphan keys** — a key set in an environment that no longer exists in the chart. This matters because the charts' `values.schema.json` is permissive (midaz has 106 `additionalProperties: true` against 2 `false`), so `helm template` accepts a key the chart dropped and the deploy silently falls back to the chart default — including for the image pin written by the image-tag path.

### Why breaking is the point

A chart that adds a required key, renames one or drops one **fails the bump**. Nothing is rewritten to make it pass.

That is deliberate. This GitOps repository is the internal tier, and its job is to surface what an upgrade demands before the same chart reaches an external client. Repairing values automatically here would hide exactly the signal the tier exists to produce: the work would not disappear, it would reappear downstream with nobody warned.

So the failure is the deliverable. Someone reads it, updates the values by hand, and now knows precisely what the upgrade note for external consumers has to say.

An earlier revision of this composite applied chart-declared migrations (`rename`, `remove`, `require`) to make bumps pass unattended. It was removed for the reason above.

## Usage as a composite step

```yaml
- name: Update the pinned chart version
  uses: LerianStudio/github-actions-shared-workflows/src/deploy/gitops-chart-update@tier-2
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
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-chart-update.yml@tier-2
    with:
      chart_name: midaz
      chart_version: 9.1.0
      chart_ref: oci://ghcr.io/lerianstudio/midaz-helm
    secrets: inherit
```

## Third-party actions

| Action | Why |
|---|---|
| `actions/checkout` | The canonical checkout. Used twice with different trust settings: the GitOps repository with a write token and `persist-credentials: false`, and the deployment matrix as a sparse, read-only checkout |
| `helmfile/helmfile-action` | The maintained installer from the helmfile project. Chosen over downloading the release archive because piping `curl` into `sudo tar` installs an unverified binary that then executes as part of the render gate |
| `crazy-max/ghaction-import-gpg` | Already the org standard for signing commits in `gitops-update.yml` and the chart release pipeline. The target repository ruleset requires signed commits, and this handles the passphrase-protected CI key |

All three are pinned by commit SHA with the version in a trailing comment, as third-party actions require.

## Required permissions

```yaml
permissions:
  contents: read
```

Write access to the GitOps repository comes from `gitops-token`, not from the job's `GITHUB_TOKEN`. The token is never persisted in the checkout: `helmfile` can execute release hooks against it, so credentials are supplied to git only at push time.
