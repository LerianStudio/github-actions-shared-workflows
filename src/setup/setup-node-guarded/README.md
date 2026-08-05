<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>setup-node-guarded</h1></td>
  </tr>
</table>

Composite action that sets up Node (and pnpm when needed) and installs dependencies **through [Socket Firewall](https://github.com/SocketDev/sfw-free)**, so a malicious package is refused before any install script runs.

It replaces the pnpm-setup + node-setup + install trio that `frontend-pr-analysis.yml` repeats in twelve jobs. That duplication is why the gap existed: a firewall shim only protects installs in its own job, so guarding one job left eleven others running `npm ci` unprotected — with the runner's tokens in scope for any `postinstall`.

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `package-manager` | Package manager used to install dependencies (`npm`, `yarn`, `pnpm`) | No | `npm` |
| `node-version` | Node.js version to set up | No | `22` |
| `working-dir` | Directory holding the `package.json` and lockfile | No | `.` |
| `guard` | Route the install through Socket Firewall. `false` restores the pre-Socket behaviour, cache included | No | `true` |
| `firewall-version` | Socket Firewall binary version | No | `latest` |
| `job-summary` | Socket Firewall job summary verbosity (`all`, `errors`, `none`) | No | `errors` |
| `use-cache` | Cache the `sfw` binary. Unrelated to the package-manager cache | No | `true` |
| `github-token` | Token used by Socket Firewall to download its binaries. Empty falls back to `github.token` | No | `''` |
| `fail-on-block` | Fail the step when Socket Firewall blocks a package | No | `true` |

## Outputs

| Output | Description |
|---|---|
| `guarded` | `true` when the install actually ran through Socket Firewall |
| `blocked` | `true` when the guarded install failed and the output carries a Socket block marker |
| `install-exit-code` | Exit code returned by the package manager install |
| `report-path` | Path to the Socket Firewall report JSON, empty when unguarded |

## Guarded and unguarded modes

The two modes differ in one deliberate way: **the guarded path has no package-manager cache.**

Socket Firewall free is a wrapper around the package manager and only sees what crosses the network. Per its documentation, *"if there are no network requests, as is the case when artifacts are cached locally, there is nothing for `sfw` to block"*. A restored cache would therefore let tarballs install uninspected. So the guarded path:

- does not pass `cache:` to `actions/setup-node` (which also stops this job from writing a post-run cache entry other jobs would restore);
- purges the package manager's cache (`npm cache clean --force`, `yarn cache clean`, `pnpm store prune`) before installing, since a runner image can arrive pre-warmed anyway;
- prefixes the install with `sfw`, which is the only supported form in the pinned `SocketDev/action` release — it exposes no `shims` input, so a bare `npm ci` would install completely uninspected while still reporting success.

The measured cost of losing the cache is small: a cold `sfw npm ci` over ~2000 packages runs in roughly 20s.

`guard` also degrades to unguarded on its own when no lockfile is present in `working-dir`, with a `::warning::` — nothing is fetched, so there is nothing to inspect.

## How the verdict is decided

| Install exit | Block marker | `fail-on-block` | Result |
|---|---|---|---|
| `0` | — | any | Step passes |
| non-zero | present | `true` | `::error::` + step fails |
| non-zero | present | `false` | `::warning::` + step passes |
| non-zero | absent | any | `::error::` + step fails |

A broken install is **always** a failure — swallowing it would hide a genuine problem behind a security toggle, so `fail-on-block: false` only softens confirmed Socket blocks.

## Usage

### As a composite step

```yaml
jobs:
  lint:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - uses: actions/checkout@v6
        with:
          persist-credentials: false

      - name: Setup Node.js and install dependencies
        uses: LerianStudio/github-actions-shared-workflows/src/setup/setup-node-guarded@v1
        with:
          package-manager: 'npm'
          node-version: '22'
          working-dir: '.'

      - run: npx eslint .
```

### Via the reusable workflow

Every install job in `frontend-pr-analysis` uses it, and `js-pr-validation` forwards the toggle:

```yaml
jobs:
  pr-validation:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/js-pr-validation.yml@v1.x.x
    with:
      socket_enable_firewall: true   # default — forwarded as `guard`
      socket_fail_on_block: true     # default
    secrets: inherit
```

Set `socket_enable_firewall: false` for a repository that cannot install without a private registry: the firewall free edition does not support custom registries.

## Permissions required

```yaml
permissions:
  contents: read
```

## Third-party actions used

| Action | Why |
|---|---|
| [`SocketDev/action`](https://github.com/SocketDev/action) | Vendor-maintained installer for the `sfw` binary, with version resolution and checksum verification. Pinned by commit SHA (`v1.3.2`). |
| [`actions/setup-node`](https://github.com/actions/setup-node) | Provides the Node.js runtime. Invoked twice under mutually exclusive conditions so the guarded path can omit the cache. |
| [`pnpm/action-setup`](https://github.com/pnpm/action-setup) | `pnpm` is not preinstalled on the runner; only used when `package-manager: pnpm`. |
