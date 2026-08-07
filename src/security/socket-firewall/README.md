<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>socket-firewall</h1></td>
  </tr>
</table>

Composite action that installs [Socket Firewall](https://github.com/SocketDev/sfw-free) (free edition, no account required) and then runs the project's dependency install through it as `sfw npm ci` (or the `yarn`/`pnpm` equivalent). `sfw` intercepts the package manager's network traffic, inspects each package as it is fetched and refuses the ones whose behavior matches a supply-chain attack — malicious install scripts, credential exfiltration, typosquats, hijacked patch releases.

This is the install-time layer. It refuses a malicious package before it reaches disk, but reports nothing about what it allowed and enforces no policy of its own — for the verdict see [`socket-app-gate`](../socket-app-gate/README.md), and for per-package findings see [`socket-api-report`](../socket-api-report/README.md).

> Most installs in the pipeline go through [`setup-node-guarded`](../../setup/setup-node-guarded/README.md), which wraps this same firewall around each analysis job's install. This composite is the dedicated one in the `socket` job, used as the reporting source.

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `package-manager` | Package manager used to install dependencies (`npm`, `yarn`, `pnpm`) | No | `npm` |
| `node-version` | Node.js version used for the guarded install | No | `22` |
| `working-dir` | Directory holding the `package.json` and lockfile | No | `.` |
| `firewall-version` | Socket Firewall binary version. `latest` tracks the newest release | No | `latest` |
| `job-summary` | Socket Firewall job summary verbosity (`all`, `errors`). `none` is coerced to `errors` | No | `all` |
| `use-cache` | Cache the `sfw` binary between runs. Unrelated to the package-manager cache, which is always purged | No | `true` |
| `github-token` | Token used by Socket Firewall to download its binaries. Empty falls back to `github.token` | No | `''` |
| `fail-on-block` | Fail the step when Socket Firewall blocks a package | No | `true` |
| `dry-run` | Print the resolved configuration and never fail the step | No | `false` |

## Outputs

| Output | Description |
|---|---|
| `skipped` | `true` when no lockfile was found in `working-dir`, so nothing was installed or inspected |
| `blocked` | `true` when the Socket Firewall report records at least one blocked package |
| `blocked-count` | Number of packages Socket Firewall refused |
| `findings-file` | Path to the report JSON, for consumption by `socket-reporter` |
| `install-exit-code` | Exit code returned by the package manager install |
| `report-path` | Path to the Socket Firewall report JSON produced by the underlying action |

## Two things that would silently defeat this

Socket Firewall free works as a wrapper: it only sees what the package manager sends over the network, and only for processes it actually parents. Two easy mistakes turn the whole check into a no-op that still reports success.

**1. Running the package manager without the `sfw` prefix.** The pinned release (`v1.3.2`) installs the `sfw` binary onto `PATH` and nothing else — it declares no `shims` input and creates no wrapper scripts. A bare `npm ci` therefore never involves `sfw`. Every command here is prefixed, which is the only supported form in that release.

**2. Installing from a warm package-manager cache.** Per Socket's documentation, "if there are no network requests, as is the case when artifacts are cached locally, there is nothing for `sfw` to block". This action therefore does **not** pass `cache:` to `actions/setup-node`, and purges the selected package manager's cache (`npm cache clean --force`, `yarn cache clean`, `pnpm store prune`) immediately before the install. A pre-warmed runner image is otherwise enough to hide a malicious package.

The `use-cache` input is unrelated to either: it caches the `sfw` binary itself, not packages.

## No lockfile, no run

Before touching the toolchain the action checks for the lockfile matching `package-manager` (`package-lock.json`, `yarn.lock` or `pnpm-lock.yaml`) inside `working-dir`. If it is absent, everything is skipped with a `::warning::` and `skipped=true`.

That keeps monorepos — whose manifests live under a subdirectory — from going red on a configuration gap: they get a warning pointing at `working-dir` instead of a failed install.

## How the verdict is decided

A blocked package surfaces as a non-zero exit from the package manager running under `sfw`, so a failing install is either a Socket block or an ordinary dependency resolution problem. The action separates the two by reading the **Socket Firewall JSON report** (`blocked[]`), not by matching text in the install output — the report is the only source that names the refused packages and survives a truncated log.

That is also why `job-summary: none` is coerced to `errors`: the pinned action exports the report path only when the summary is not `none`, and without the report a genuine block is indistinguishable from a broken install.

| Install exit | Report records a block | `fail-on-block` | Result |
|---|---|---|---|
| `0` | no | any | Step passes |
| any | yes | `true` | `::error::` + step fails |
| any | yes | `false` | `::warning::` + step passes |
| non-zero | no | any | `::error::` + step fails |

A broken install is **always** a failure. Swallowing it would hide a genuine problem behind a security toggle, so `fail-on-block: false` only softens confirmed Socket blocks.

With `dry-run: true` nothing is fetched and nothing is installed: the action prints the resolved configuration and skips the firewall setup, the cache purge, the install and the evaluation. A dry run is a preview, not a scan.

## Usage

### As a composite step

```yaml
jobs:
  socket:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - uses: actions/checkout@v6
        with:
          persist-credentials: false

      - name: Socket Firewall
        uses: LerianStudio/github-actions-shared-workflows/src/security/socket-firewall@v1
        with:
          package-manager: 'npm'
          node-version: '22'
          working-dir: '.'
```

### Via the reusable workflow

Socket Firewall is wired into the `js-pr-validation` umbrella and enabled by default:

```yaml
jobs:
  pr-validation:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/js-pr-validation.yml@v1.x.x
    with:
      run_socket: true                # default
      socket_enable_firewall: true    # default
      socket_fail_on_block: true      # default
    secrets: inherit
```

## Permissions required

```yaml
permissions:
  contents: read
```

## Third-party actions used

| Action | Why |
|---|---|
| [`SocketDev/action`](https://github.com/SocketDev/action) | Vendor-maintained installer for the `sfw` binary, including version resolution and checksum verification. Reimplementing the download inline would mean hand-rolling that verification. Pinned by commit SHA (`v1.3.2`). |
| [`actions/setup-node`](https://github.com/actions/setup-node) | Provides the Node.js runtime the package manager needs. Used **without** its cache feature, for the reason above. |
| [`pnpm/action-setup`](https://github.com/pnpm/action-setup) | `pnpm` is not preinstalled on the runner; only used when `package-manager: pnpm`. |

This composite adds what the vendor action does not cover: the toolchain, the cache purge, the `sfw`-prefixed install, block-versus-failure attribution and the advisory mode.
