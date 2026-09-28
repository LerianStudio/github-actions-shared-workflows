# Build Workflow

Reusable workflow for building and pushing Docker images to container registries. Supports monorepo architectures with automatic change detection and multi-platform builds.

## Features

- **Monorepo support**: Builds every component listed in `filter_paths` by default; set `force_full_matrix: false` to build only changed components
- **Multi-registry**: Push to DockerHub and/or GitHub Container Registry (GHCR)
- **Smart platform builds**: Beta/RC tags build amd64 only (unless `force_multiplatform` is enabled), release tags build amd64+arm64
- **Semantic versioning**: Automatic tag extraction and Docker metadata
- **GitOps integration**: Upload artifacts for downstream gitops-update workflow
- **Slack notifications**: Automatic success/failure notifications

## Usage

### Single App Repository

```yaml
name: Build
on:
  push:
    tags:
      - '**'

jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/build.yml@tier-1
    with:
      runner_type: "firmino-lxc-runners"
      enable_dockerhub: true
      enable_ghcr: true
      dockerhub_org: lerianstudio
    secrets: inherit
```

### Monorepo with Multiple Components

```yaml
name: Build
on:
  push:
    tags:
      - '**'

jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/build.yml@tier-1
    with:
      runner_type: "firmino-lxc-runners"
      filter_paths: |-
        components/onboarding
        components/transaction
        components/console
      path_level: 2
      app_name_prefix: "midaz"
      enable_dockerhub: true
      enable_ghcr: true
      dockerhub_org: lerianstudio
      enable_gitops_artifacts: true
    secrets: inherit
```

### With GitOps Update

```yaml
name: Build
on:
  push:
    tags:
      - '**'

jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/build.yml@tier-1
    with:
      filter_paths: |-
        components/api
        components/worker
      path_level: 2
      app_name_prefix: "myapp"
      enable_gitops_artifacts: true
    secrets: inherit

  update_gitops:
    needs: [build]
    if: contains(github.ref, '-beta') || contains(github.ref, '-rc')
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@tier-1
    with:
      gitops_repository: "MyOrg/gitops-repo"
      artifact_pattern: "gitops-tags-myapp-*"
    secrets: inherit
```

## Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `runner_type` | string | `firmino-lxc-runners` | GitHub runner type |
| `build_runner_type` | string | `''` | Optional runner override for the Build jobs only (prepare/notify stay on `runner_type`); empty falls back to `vars.GENERAL_RUNNERS`, then `runner_type` |
| `filter_paths` | string | `''` | Newline-separated list of path prefixes. If empty, builds from root (single-app mode) |
| `path_level` | string | `2` | Directory depth for app name extraction |
| `enable_dockerhub` | boolean | `true` | Enable pushing to DockerHub |
| `enable_ghcr` | boolean | `true` | Enable pushing to GitHub Container Registry (requires `MANAGE_TOKEN`) |
| `dockerhub_org` | string | `lerianstudio` | DockerHub organization name |
| `ghcr_org` | string | `''` | GHCR organization (defaults to repository owner) |
| `on_existing_tag` | string | `fail` | Behaviour when the target tag already exists in an enabled registry (pre-flight check before build): `fail` (abort early), `skip` (skip build/push when every enabled registry already has the tag, still emitting GitOps artifacts for an idempotent re-run; abort on a partial publish), `repair` (same as `skip`, but on a partial publish push only to the registries missing the tag), `warn` (warn and build anyway) |
| `require_image_provenance` | boolean | `true` | Under `on_existing_tag: skip`/`repair`, abort when the existing image does not record the commit it was built from (`org.opencontainers.image.revision`). An image whose recorded commit *differs* from this run always aborts, regardless of this input. Set `false` to accept unverifiable images (e.g. tags published before the label was emitted). Images published before this workflow set the label explicitly are recognised by their legacy `github.sha` value, so re-running an older tag is not blocked |
| `require_build_identity` | boolean | `false` | Fail the build when the Dockerfile does not declare `ARG REVISION`. Set it once the service has adopted the compiled build identity so a regression cannot ship. Without it a removed `ARG REVISION` only downgrades to a warning. See [Build identity contract](#build-identity-contract) |
| `dockerfile_name` | string | `Dockerfile` | Name of the Dockerfile |
| `tag_prefix` | string | `''` | Skip this build entirely (`has_builds=false`) when triggered by a tag that does not start with this prefix. For callers with multiple independently-tagged components sharing one workflow_call chain. Empty = build on every tag |
| `app_name_prefix` | string | `''` | Prefix for app names in monorepo |
| `build_context` | string | `.` | Docker build context |
| `enable_gitops_artifacts` | boolean | `false` | Upload artifacts for gitops-update workflow |
| `force_full_matrix` | boolean | `true` | Build all `filter_paths` components on every run regardless of what changed. Set `false` to build only changed components |
| `force_multiplatform` | boolean | `false` | Force multi-platform build (amd64+arm64) even for beta/rc tags |
| `enable_cosign_sign` | boolean | `true` | Sign images with cosign keyless (OIDC) signing. Requires `id-token: write` in caller |
| `cosign_max_attempts` | string | `5` | Max cosign signing attempts per image. Increase to absorb transient OIDC/Fulcio/Rekor rate limits |
| `cosign_initial_delay` | string | `5` | Initial delay (seconds) between cosign retries. Grows ×3 each failed attempt, capped at `cosign_max_delay`, then randomized (equal jitter) |
| `cosign_max_delay` | string | `60` | Maximum delay (seconds) between cosign retries. Caps the exponential backoff before jitter is applied |
| `continue_gitops_on_signing_failure` | boolean | `false` | Allow GitOps artifact upload to continue when cosign signing fails after all retries. Image stays unsigned in registry; manual `cosign sign` required |

## Secrets

Uses `secrets: inherit` pattern. Required secrets:

| Secret | Description | Required When |
|--------|-------------|---------------|
| `DOCKER_USERNAME` | DockerHub username | `enable_dockerhub: true` |
| `DOCKER_PASSWORD` | DockerHub password/token | `enable_dockerhub: true` |
| `MANAGE_TOKEN` | GitHub token for GHCR | `enable_ghcr: true` |
| `SLACK_WEBHOOK_URL` | Slack webhook for notifications | Optional |

## Tag Immutability and Re-runs

Before building, the workflow checks whether the target image tag already exists in each enabled registry (via `docker manifest inspect`, reusing the registry logins). This avoids a full rebuild that would only fail at push time on registries with tag immutability enabled. Behaviour is controlled by `on_existing_tag`:

- **`fail`** (default): abort early with a clear error instead of rebuilding then failing at push.
- **`skip`**: skip the build/push but still emit the GitOps tag artifacts (from the version), so a re-run remains idempotent for the downstream GitOps update. Cosign signing (if enabled) also retries in this mode: the digest is resolved from the existing registry tag via `docker buildx imagetools inspect` instead of the build/push step, so a transient signing failure on an already-pushed tag can be recovered with a plain re-run instead of cutting a new release. The skip requires the tag in **every** enabled registry — see partial publishes below.
- **`repair`**: same as `skip`, plus it repairs a partial publish instead of aborting on it. Opt-in — see partial publishes below.
- **`warn`**: emit a warning and build anyway (push may still fail on immutable registries).

`docker manifest inspect` exits non-zero both when the tag is absent and when the lookup itself fails, so the pre-flight reads the registry's error text to tell the two apart — a tag is only treated as missing when the registry actually reports it absent. When no registry confirms the tag, an errored check still counts as "not present" and the build proceeds, so a flaky check never blocks a legitimate build.

When one registry confirms the tag and another could not be reached, `skip` and `repair` abort naming the unreachable registry: an undetermined status is not evidence of a partial publish, and guessing either way is wrong (`skip` would publish a GitOps reference it cannot vouch for, `repair` would push to a registry that may already hold the immutable tag). A re-run once the registry answers is enough. `fail` and `warn` are unaffected — neither depends on which registries are missing the tag.

### Partial publishes

When more than one registry is enabled, a previous run can have published to one and failed on the other (e.g. the DockerHub push succeeded and the GHCR push did not). Skipping outright there would emit a GitOps tag artifact for a tag that is missing from an enabled registry, so `skip` short-circuits **only** when every enabled registry already has the tag:

| Tag present in | `fail` (default) | `skip` | `repair` | `warn` |
|---|---|---|---|---|
| no registry | build | build | build | build |
| some registries | abort | **abort**, naming the missing ones | build, push **only** to the missing ones | build, push to all |
| every registry | abort | skip, emit GitOps artifacts | skip, emit GitOps artifacts | build, push to all |

A partial publish is an accident, not a normal state, so the default path is to stop and report it rather than paper over it. Prefer removing the partially published tag and cutting a fresh run, or cut a new version outright.

`repair` exists for the residual case that cleanup cannot reach: a registry with tag immutability enabled, where deleting the partially published tag is not possible at all. It builds once and pushes only where the tag is missing, leaving the immutable tags already in place untouched. Cosign then signs each registry with its own digest read back from that registry, since a rebuild is not bit-for-bit reproducible and the newly pushed digest does not describe the image the other registry already carries.

### Image provenance

Tag existence alone does not prove the image in the registry is the code this run is building. Two situations look identical to a `docker manifest inspect`:

- **A genuine re-run.** The push succeeded earlier and something after it failed (cosign, the GitOps upload, the Helm dispatch). The registry image *is* the merged code — this is what `skip` is for.
- **A retargeted tag.** A released semver tag was deleted and recreated on a newer commit. Registry tags are immutable, so the registry still holds the image built from the **old** commit. Skipping would have GitOps deploy the older code, and repairing would leave the registries holding different content under one tag.

So before `skip` or `repair` reuses an existing tag, the pre-flight reads `org.opencontainers.image.revision` off the existing image (`docker buildx imagetools inspect`) and compares it with the commit this run checked out. This workflow sets that label explicitly from the same `REVISION` it compiles into the image (see [Build identity contract](#build-identity-contract)), overriding the `docker/metadata-action` default of `github.sha` — which is the wrong commit whenever `checkout_ref` points elsewhere, as it does on every release.

| Recorded commit | Behaviour |
|---|---|
| matches this run | proceed with `skip` / `repair` as described above |
| matches `github.sha` (legacy label) | proceed — images published before this workflow set the label explicitly carry the `docker/metadata-action` default, which on a release is the branch commit rather than the tag commit. Transitional: the comparison drops once no such tag can still be re-run |
| differs from this run | **abort**, naming both commits — always, regardless of `require_image_provenance` |
| absent, or the lookup failed | abort when `require_image_provenance: true` (default); warn and proceed when `false` |

A confirmed different commit is never a re-run, so it is not something an input should be able to wave through. `require_image_provenance` governs only the can't-tell case — set it to `false` for repositories whose registry still holds tags published before the label was emitted, and images that *do* carry the label are still checked.

`fail` and `warn` never reach this gate: neither reuses an existing image.

Retargeting a released semver tag stays an anti-pattern — cut a new patch version instead. The gate is there so CI fails loudly rather than deploying stale code quietly.

## Platform Build Strategy

The workflow automatically selects platforms based on the tag type:

| Tag Type | `force_multiplatform` | Platforms | Rationale |
|----------|----------------------|-----------|-----------|
| Beta | `false` (default) | `linux/amd64` | Faster CI for development |
| Beta | `true` | `linux/amd64,linux/arm64` | Multi-arch needed in dev |
| RC | `false` (default) | `linux/amd64` | Faster CI for staging |
| RC | `true` | `linux/amd64,linux/arm64` | Multi-arch needed in staging |
| Release | N/A | `linux/amd64,linux/arm64` | Always full multi-arch support |

## Docker Image Tags

Generated tags based on semantic versioning:

| Tag Pattern | Example | When Applied |
|-------------|---------|--------------|
| `{{version}}` | `1.0.0-beta.1` | Always |

Only the exact version is published. Floating aliases (`1`, `1.12`) are not:
re-pointing an existing alias is refused by Docker Hub immutable-tag rules and
fails the whole build. Consumers must pin the exact version.

## Build Arguments

Every image build receives the `docker_build_args` input first, then three build
arguments this workflow computes — the build identity contract:

| Build argument | Value | Example |
|----------------|-------|---------|
| `VERSION` | The resolved release version, SemVer — the `release_version` input, or the version parsed out of the git tag, with any leading `v` stripped | `1.4.0` |
| `REVISION` | Full 40-hex commit SHA of `HEAD` after the checkout, i.e. the commit this run actually builds | `e83c5163…7a9f0b2c` |
| `BUILD_TIME` | Build timestamp, RFC3339 UTC, captured once per app | `2026-08-28T14:03:11Z` |

`VERSION` is normalized once, at the source: both the tag-push path (`v1.4.0`) and
the same-run branch-push path (`1.4.0`, from semantic-release) yield the bare
semver. It is the same string the image is published under and the same string the
GitOps tag artifact carries, so nothing downstream has to strip anything.

`REVISION` is read with `git rev-parse HEAD` after the checkout, not from
`github.sha`. On the release path those two differ: the tag semantic-release
created points at the CHANGELOG commit made inside the same run. The same SHA
feeds the `org.opencontainers.image.revision` label and the pre-flight provenance
comparison, so the image, the label and the gate all name one commit.

`VERSION` cannot be passed through `docker_build_args` by a caller of
`go-release.yml`: semantic-release computes the release version inside that
workflow, after the static input is already bound. The primary build and every
`extra_builds` group get all three arguments, because both route through this
workflow.

`BUILD_TIME` changes on every run, so the layers from its `ARG` onward rebuild
each time; put the three `ARG` lines as late as the build stage allows to keep
dependency layers cached.

## Build identity contract

An image that cannot say what it is costs an on-call engineer the first ten
minutes of every incident. So a published image compiles its own identity in and
answers for it: `docker run <image> --version` prints the version it was published
under and the commit it was built from, and CI refuses to push an image whose
answer disagrees with what it injected.

### What a service adopts

The Dockerfile declares the three arguments and compiles them into the binary:

```dockerfile
ARG TARGETARCH
ARG VERSION=dev
ARG REVISION=unknown
ARG BUILD_TIME=unknown
RUN CGO_ENABLED=0 GOOS=linux GOARCH=${TARGETARCH} \
    go build -trimpath -buildvcs=false \
      -ldflags="-s -w -X main.version=${VERSION} -X main.revision=${REVISION} -X main.buildTime=${BUILD_TIME}" \
      -o /service ./cmd/app
```

`-buildvcs=false` because CI supplies the revision and the builder does not need
the `git` binary. `ENTRYPOINT` must be the binary itself, with no shell wrapper,
or `docker run <image> --version` never reaches the flag.

`main` declares the three variables and hands them to the shared package:

```go
package main

import "github.com/LerianStudio/lib-commons/v7/commons/buildinfo"

// Filled at build time via -ldflags -X main.<name>. Empty in a local build.
var version, revision, buildTime string

func main() {
	buildinfo.Set(buildinfo.Build{Version: version, Revision: revision, BuildTime: buildTime})
	buildinfo.HandleFlag() // "--version" prints the identity as JSON and exits 0

	// ... normal bootstrap
}
```

The symbol names `main.version`, `main.revision` and `main.buildTime` are stable
forever. The `-X` target is `main`, never the library, so a lib-commons major bump
never touches the Dockerfile.

### What CI verifies

For an image whose Dockerfile has adopted the contract, this workflow builds the
image for the runner's native platform first, runs `--version` against it, and only then builds and pushes the real
multi-arch image. The local image is tagged `build-identity-verify/<app>:<version>`
and never leaves the runner; its layers land in the GitHub Actions cache, so the
push build reuses them for that platform instead of compiling it twice.

The check runs the image with no network and never pulls it, so a tag that is
not in the runner's daemon fails locally:

```bash
docker run --rm --pull=never --network none "$IMAGE" --version
```

and is exact equality on two fields of the JSON it prints, `version` and
`revision`, against what CI injected. Every field read back (`version`,
`revision`, `goVersion`, `service`) is untrusted output of the image, so each
must be at most 64 characters of `A-Z a-z 0-9 . _ + -` (`service` without `+`)
before it is compared or written into an annotation. A value outside that set
fails the build with a fixed message that does not repeat it: a binary could
otherwise print a line that the runner executes as a workflow command.

The verification is a `run:` step inside `build.yml`, not a composite action.
The runner resolves every `uses:` of a job before any step condition runs, for
every repository that calls this workflow, so a composite would be one more
reference every release depends on, adopted or not.

| Failure | What it means | Fix |
|---|---|---|
| `did not answer --version with JSON` | `ENTRYPOINT` is a shell wrapper, or `main` never calls `buildinfo.HandleFlag()` | Make the binary the `ENTRYPOINT`; call `HandleFlag()` before bootstrap |
| `docker run … --version failed or timed out` | Same, or the binary started the service instead of exiting | As above |
| `reports version X, CI built Y` | `ARG VERSION` missing, not passed to `-X main.version`, or `buildinfo.Set` not called | Add the `ARG`, the `-ldflags` entry, and the `Set` call |
| `reports revision X, CI built Y` | Same, for `ARG REVISION` / `-X main.revision` | As above |
| `reports a <field> outside the allowed character set` | The binary prints something other than the `buildinfo` identity JSON for that field | Print the identity with `buildinfo.HandleFlag()`; run the reproduce command locally to see the value |

### Adoption

Verification runs when the app's Dockerfile declares `ARG REVISION` — the single
line that says the image compiles its identity in. Without it the build proceeds
as before — Docker only warns about an unused build argument, and an undeclared
argument does not invalidate the build cache — and the job emits a warning naming
the image and this section.

`require_build_identity: true` turns that warning into a failure, so a Dockerfile
that loses `ARG REVISION` fails the build instead of shipping an image without its
identity. `go-release.yml` always sets it for its primary image and defaults it to
`true` for its `extra_builds` groups: every Go service image released through it
proves its identity, and a group without a Go binary opts out with
`"require_build_identity": false` (see [go-release, Build identity](go-release.md#build-identity)).
Here the input still defaults to `false`: the repositories that call this workflow
directly publish TypeScript and Python images, which do not carry the contract.

Local builds pass no arguments, report `dev` / `unknown`, and are not blocked.
Images published by CI are.

### How verification is tested

Two suites in `tests/build-identity/` run in the `Build Identity Verification
Tests` job of `self-pr-validation.yml`. Both extract the shell blocks they test out
of `build.yml` and run them as written, so the workflow is what the assertions
bind to, not a copy of it.

`test.sh` runs the `Verify build identity` step against throwaway `FROM scratch`
images built on the spot, and needs `docker`, `go` and `jq`. It covers a matching
identity, a version mismatch, a revision mismatch, a binary whose linker flags
were never wired (the half-adoption shape) and its revision-only half, an image
that ignores `--version`, one that never answers before the timeout, a workflow
command injected through `goVersion`, `version` and `service` values outside the
allowed set, a missing local image, and each required input. `docker` is shimmed
on `PATH` so any `docker run` without `--pull=never` and `--network none` fails.

`test-workflow.sh` runs the version-resolution and adoption-gate blocks against a
case table, including the warning a non-adopting image gets and the failure it
gets instead under `require_build_identity`, then reads `build.yml`
as text to pin the wiring that makes verification a pre-push gate: step order, a
verification build that loads instead of pushing, the same version and revision fed
to both builds and to the check, the check gated on adoption, and the gate reading
`require_build_identity`. It needs neither
`docker` nor `go`.

```bash
bash tests/build-identity/test.sh
bash tests/build-identity/test-workflow.sh
shellcheck tests/build-identity/*.sh
```

## Monorepo Change Detection

When `filter_paths` is provided, the workflow:

1. Detects which components have changes in the tagged commit
2. Builds only the changed components
3. Names images using the pattern: `{app_name_prefix}-{component_name}`

**Example:**

```yaml
filter_paths: |-
  components/api
  components/worker
app_name_prefix: "myapp"
```

Changed files in `components/api/` → Builds `myapp-api` image
Changed files in `components/worker/` → Builds `myapp-worker` image

## GitOps Artifacts

When `enable_gitops_artifacts: true`:

1. Creates artifact files with version tags (without `v` prefix)
2. Uploads as GitHub Actions artifacts
3. Can be consumed by `gitops-update.yml` workflow

**Artifact pattern:** `gitops-tags-{app_name}`

## Helm Dispatch

When `enable_helm_dispatch: true`, the workflow dispatches a chart update to the configured Helm repository (default: `LerianStudio/helm`) after a successful build.

### Default policy: production releases only

By default, Helm dispatch runs **only on production release tags** (non-`-rc`, non-`-beta`). This is enforced by:

- `helm_dispatch_on_rc` → `default: false`
- `helm_dispatch_on_beta` → `default: false`

This is intentional. RC and beta tags are pre-release artifacts — dispatching them to the Helm repo creates noisy PRs in `LerianStudio/helm` for charts that should not roll forward to staging or production.

### Opt-in for RC/beta dispatch (use sparingly)

Only enable `helm_dispatch_on_rc` or `helm_dispatch_on_beta` when there is a deliberate reason — for example, a chart that must be staged from RC builds in a specific environment. Document the reason in the caller workflow.

```yaml
# ✅ Correct — production-only dispatch (recommended)
jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/build.yml@tier-1
    with:
      enable_helm_dispatch: true
      helm_chart: my-chart
      # helm_dispatch_on_rc and helm_dispatch_on_beta default to false
    secrets: inherit
```

```yaml
# ⚠️ Opt-in — only when intentional, document why
jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/build.yml@tier-1
    with:
      enable_helm_dispatch: true
      helm_chart: my-chart
      helm_dispatch_on_rc: true   # staging environment promotes from RC tags
    secrets: inherit
```

## Slack Notifications

Automatically sends notifications on completion:

- ✅ **Success**: Green notification with workflow details
- ❌ **Failure**: Red notification with failed job names
- Skipped if `SLACK_WEBHOOK_URL` secret is not configured

## Workflow Jobs

### prepare
- Detects changed paths (monorepo) or sets single-app mode
- Determines build platforms based on tag type
- Outputs matrix for build job

### build
- Runs for each component in the matrix
- Verifies the image reports the identity CI injected, before anything is pushed (see [Build identity contract](#build-identity-contract))
- Builds and pushes Docker images
- Creates GitOps artifacts if enabled

### notify
- Sends Slack notification on completion

## Image Signing (cosign)

Container images are signed by default using [Sigstore cosign](https://github.com/sigstore/cosign) with keyless (OIDC) signing. The GitHub Actions identity is used as proof of provenance — no private keys are needed.

### Caller permissions

Callers **must** grant `id-token: write` for signing to work:

```yaml
permissions:
  contents: read
  packages: write
  id-token: write   # required for cosign keyless signing
```

### Disabling signing

```yaml
jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/build.yml@tier-1
    with:
      enable_cosign_sign: false
    secrets: inherit
```

### Resilience: retries and GitOps continuation

Cosign signing depends on the Sigstore OIDC/Fulcio infrastructure, which can hit transient rate limits or 5xx responses. Two layers protect releases:

1. **Retry with exponential backoff and jitter** — controlled by `cosign_max_attempts` (default `5`) and `cosign_initial_delay` (default `5`s, grows ×3 between attempts, capped at `cosign_max_delay` — default `60`s — then randomized with equal jitter to avoid multiple jobs retrying against Rekor at the same instant). Increase these for releases that consistently brush against rate limits or multi-minute Rekor outages.

2. **Optional GitOps continuation** — when `continue_gitops_on_signing_failure: true`, signing failure does not block the GitOps artifact upload. The image is already pushed and immutable in the registry; this prevents a transient signing failure from leaving the release in a broken half-state where the image exists but no GitOps PR was opened.

```yaml
jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/build.yml@tier-1
    with:
      enable_cosign_sign: true
      cosign_max_attempts: 5
      cosign_initial_delay: 15
      cosign_max_delay: 60
      continue_gitops_on_signing_failure: true
    secrets: inherit
```

When continuation kicks in, the workflow:

- Logs a `::warning::` with the unsigned digest
- Writes a "manual action required" block to the GitHub Actions step summary listing the digest and image refs
- Lets the `dispatch-helm` / GitOps job proceed normally

**Manual recovery** — sign the digest after the fact, then verify:

```bash
cosign sign --yes <registry>/<org>/<app>@<sha256-digest>
cosign verify --certificate-identity-regexp '...' --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' <ref>
```

Treat any release with a "Unsigned image" summary block as **not production-ready** until the manual sign step is completed.

### Verifying signatures

```bash
cosign verify \
  --certificate-identity-regexp="^https://github\.com/LerianStudio/.+/.github/workflows/.+@refs/(heads|tags)/.+$" \
  --certificate-oidc-issuer="https://token.actions.githubusercontent.com" \
  docker.io/lerianstudio/my-app@sha256:abc123...
```

## Best Practices

1. **Use semantic versioning tags**: `v1.0.0`, `v1.0.0-beta.1`, `v1.0.0-rc.1`
2. **Enable both registries**: DockerHub for public access, GHCR for GitHub integration
3. **Use GitOps artifacts**: For automated deployment pipelines
4. **Configure Slack**: For build notifications to your team channel

## Troubleshooting

### No builds triggered

**Issue**: Workflow runs but no images are built

**Solution**: 
- For monorepo: Ensure changed files are within `filter_paths`
- Check tag format matches expected pattern

### GHCR authentication fails

**Issue**: Cannot push to GitHub Container Registry

**Solution**:
- Ensure `MANAGE_TOKEN` has `packages: write` permission
- Check repository visibility settings

### Slow multi-arch builds

**Issue**: ARM64 builds take too long

**Solution**: ARM64 builds only run on release tags by default. Beta/RC tags build amd64 only for faster CI. If you need ARM64 on beta/rc, use `force_multiplatform: true` and be aware of the longer build times.

## Related Workflows

- [GitOps Update](gitops-update.md) - Update deployments after build
- [Release](release.md) - Create releases that trigger builds
- [Slack Notify](slack-notify.md) - Notification system

---

**Last Updated:** 2025-12-09
**Version:** 1.0.0
