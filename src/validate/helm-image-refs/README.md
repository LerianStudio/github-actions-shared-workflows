<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>Helm Image Refs</h1></td>
  </tr>
</table>

Composite action that renders a Helm chart and verifies that every container image the
render references actually exists in its registry. Intended as a gate immediately
before `helm push`: a chart that ships a reference to an image nobody published is
valid YAML, lints clean, and renders fine — it only fails once a cluster tries to pull
it.

## Behavior

The chart is rendered **with hooks**. This is the point of the action: migration Jobs
are Helm hooks, and their image tag is usually inherited from the application tag
rather than pinned. A release that bumps the app to a version for which no migration
image was ever built renders perfectly and breaks on install. `--no-hooks` would hide
exactly that case.

Image references are collected by recursive descent over `containers`,
`initContainers` and `ephemeralContainers` lists, at any depth — a `CronJob` nests its
pod spec two levels deeper than a `Deployment`. Matching the container lists rather
than any map with an `image` key keeps unrelated values (a ConfigMap with a
`data.image` entry) out of the results.

Each reference is normalized the way a registry client resolves it before being
checked, so `lerianstudio/product-console` and `docker.io/lerianstudio/product-console:latest`
are one entry. A digest reference keeps its digest; only a tagless reference gains the
implicit `:latest`.

References are then classified with `docker manifest inspect`: the command exits
non-zero both when a tag is absent and when the lookup itself could not be completed,
and only the registry's error text tells the two apart. An unrecognised error is
reported as `unknown`, never guessed as `absent` — treating a rate limit or an expired
credential as a missing image would block a release for the wrong reason. What happens
to an `unknown` is the caller's choice, via `on-unknown`.

The absence patterns are the ones `.github/workflows/build.yml` uses, minus
`pull access denied`. That error means the credential could not see the repository,
which is a failure to verify rather than evidence of absence. Nothing is lost by
excluding it: GHCR answers `manifest unknown` both for a missing tag and for a
repository that does not exist, with or without credentials.

By default only references matching `registry-allowlist` are checked. Third-party
subchart images (Bitnami and friends) are reported as skipped, which keeps a chart with
four dependencies from spending the anonymous Docker Hub rate limit on images that are
not ours to publish.

Library charts render nothing and are skipped.

### Registry credentials

`docker manifest inspect` reads the Docker CLI credential store, so the calling job
must `docker login` to every registry it wants verified **before** this step.
`helm registry login` writes to a different store and does not satisfy this. Without a
login, a private repository answers `pull access denied`, which classifies as
`unknown` — so the gate reports that it could not verify the reference rather than
claiming the image is gone. Under the default `on-unknown: fail` that still fails the
job, which is the intended outcome: a gate that cannot see the registry has not
verified anything.

## Inputs

| Input | Description | Required | Default |
| --- | --- | --- | --- |
| `chart-path` | Path to the chart directory to render. | Yes | — |
| `values-file` | Values file passed to the render. Ignored when the file does not exist. | No | `""` |
| `release-name` | Release name used for the render. Only affects templated image references. | No | `image-refs` |
| `registry-allowlist` | Comma-separated reference prefixes to check. References outside the list are reported as skipped. Ignored when `include-dependencies` is true. | No | `ghcr.io/lerianstudio,docker.io/lerianstudio` |
| `include-dependencies` | Check every reference the render produces, including subchart images. | No | `false` |
| `on-unknown` | What to do when the registry answer is inconclusive: `fail` or `warn`. | No | `fail` |
| `dry-run` | Report every reference and its verdict without failing the step. | No | `false` |

## Outputs

| Output | Description |
| --- | --- |
| `images` | JSON array of the unique image references the chart renders. |
| `missing` | JSON array of the references confirmed absent from their registry. |
| `has-missing` | `'true'` when at least one reference is confirmed absent. |

## Usage as a composite step

```yaml
jobs:
  verify-images:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    permissions:
      contents: read
      packages: read
    steps:
      - uses: actions/checkout@v4

      - uses: azure/setup-helm@v4

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Verify referenced images exist
        uses: LerianStudio/github-actions-shared-workflows/src/validate/helm-image-refs@develop
        with:
          chart-path: charts/plugin-br-bank-transfer
          values-file: .github/configs/helm-render-values/plugin-br-bank-transfer.yaml
```

## Usage as a reusable workflow

There is no reusable-workflow wrapper for this composite, and adding one would
create a workflow with no callers. A chart repository publishes from its own
release pipeline, so the gate belongs inside that job — as a step, immediately
before whatever runs `helm push`:

```yaml
      - name: Verify referenced images exist
        uses: LerianStudio/github-actions-shared-workflows/src/validate/helm-image-refs@tier-2
        with:
          chart-path: ${{ matrix.chart.working_dir }}
          values-file: .github/configs/helm-render-values/${{ matrix.chart.name }}.yaml

      - name: Release
        uses: cycjimmy/semantic-release-action@v4   # publishCmd runs helm push
```

Placing it earlier than the publishing step is the whole point: a failure there
leaves the chart unpublished, with no tag or changelog entry to roll back.

`.github/workflows/self-helm-image-refs.yml` in this repository exercises the
composite by hand against any chart in `LerianStudio/helm`.

## Required permissions

```yaml
permissions:
  contents: read
  packages: read   # only when verifying private GHCR images with GITHUB_TOKEN
```

## Why `docker manifest inspect`

The Marketplace offers registry-inspection actions, and `crane`/`skopeo` both do this
job well. `docker manifest inspect` was chosen because the Docker CLI is already
present on every runner, the calling job has already logged in to the registries for
its own build and push steps, and the error-text classification it needs is already
written, reviewed and running in `build.yml`. Adding a second tool would mean a second
credential path for no additional capability.
