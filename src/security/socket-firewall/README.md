<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>socket-firewall</h1></td>
  </tr>
</table>

Composite action that installs [Socket Firewall](https://github.com/SocketDev/sfw-free) (free edition, no account required) and then runs the project's dependency install through it. Socket Firewall shims `npm`, `yarn` and `pnpm`, inspects each package as it is fetched and refuses the ones whose behavior matches a supply-chain attack — malicious install scripts, credential exfiltration, typosquats, hijacked patch releases.

This is the free tier of Socket. It catches malicious packages at install time but produces no PR report and enforces no central policy — for that, see [`socket-scan`](../socket-scan/README.md).

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `package-manager` | Package manager used to install dependencies (`npm`, `yarn`, `pnpm`) | No | `npm` |
| `node-version` | Node.js version used for the guarded install | No | `22` |
| `working-dir` | Directory holding the `package.json` and lockfile | No | `.` |
| `firewall-version` | Socket Firewall binary version. `latest` tracks the newest release | No | `latest` |
| `job-summary` | Socket Firewall job summary verbosity (`all`, `errors`, `none`) | No | `all` |
| `use-cache` | Cache the Socket Firewall binaries between runs | No | `true` |
| `github-token` | Token used by Socket Firewall to download its binaries. Empty falls back to `github.token` | No | `''` |
| `fail-on-block` | Fail the step when Socket Firewall blocks a package | No | `true` |
| `dry-run` | Print the resolved configuration and never fail the step | No | `false` |

## Outputs

| Output | Description |
|---|---|
| `skipped` | `true` when no lockfile was found in `working-dir`, so nothing was installed or inspected |
| `blocked` | `true` when the install failed and the output carries a Socket Firewall block marker |
| `install-exit-code` | Exit code returned by the package manager install |
| `report-path` | Path to the Socket Firewall report JSON produced by the underlying action |

## No lockfile, no run

Before touching the toolchain the action checks for the lockfile matching `package-manager` (`package-lock.json`, `yarn.lock` or `pnpm-lock.yaml`) inside `working-dir`. If it is absent, everything is skipped with a `::warning::` and `skipped=true`.

That keeps monorepos — whose manifests live under a subdirectory — from going red on a configuration gap: they get a warning pointing at `working-dir` instead of a failed install.

## How the verdict is decided

The shims make a blocked package surface as a non-zero exit from the package manager itself, so a failing install is either a Socket block or an ordinary dependency resolution problem. The action separates the two by looking for a Socket block marker in the install output:

| Install exit | Block marker | `fail-on-block` | Result |
|---|---|---|---|
| `0` | — | any | Step passes |
| non-zero | present | `true` | `::error::` + step fails |
| non-zero | present | `false` | `::warning::` + step passes |
| non-zero | absent | any | `::error::` + step fails |

A broken install is **always** a failure. Swallowing it would hide a genuine problem behind a security toggle, so `fail-on-block: false` only softens confirmed Socket blocks.

With `dry-run: true` the install still runs through the firewall and everything is reported, but the step never fails.

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

## Why this action

Socket Firewall ships as a binary plus package-manager shims, which is awkward to install correctly inline. [`SocketDev/action`](https://github.com/SocketDev/action) is the vendor-maintained installer, so this composite wraps it (pinned by commit SHA) and adds the parts it does not cover: the toolchain setup, the guarded install itself, block-versus-failure attribution and the advisory mode.
