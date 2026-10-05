<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>go-private-modules</h1></td>
  </tr>
</table>

Composite action that populates the Go module cache with private modules **using a credential that never outlives the step**. It replaces the `Fetch private Go modules` block that `go-pr-analysis.yml` repeated in seven jobs, byte for byte — a three-line correction there was seven edits that had to not drift.

## What it does

1. Writes `url.https://<token>@github.com/.insteadOf https://github.com/` into a git config file under `$RUNNER_TEMP`, pointed at by `GIT_CONFIG_GLOBAL` — never into the runner's real global config.
2. Runs `go mod download` for every module at or below `working-dir`, plus the module that *encloses* it when the directory is not a module root itself.
3. Deletes the config file on exit, via a `trap`. Everything that runs afterwards — Makefile target, linter, test binary — resolves its dependencies from the warm module cache, with no credential on disk.

The confinement is the point, not a detail. Every caller job reaches the branch's Makefile sooner or later, and `make -n` is not the escape hatch it looks like: GNU make expands `$(shell ...)` while parsing, so a probe run alone is enough for a Makefile to read whatever the job still holds.

## Usage

```yaml
- name: Fetch private Go modules
  if: inputs.go_private_modules != ''
  uses: LerianStudio/github-actions-shared-workflows/src/setup/go-private-modules@v1
  with:
    go-private-modules: ${{ inputs.go_private_modules }}
    manage-token: ${{ secrets.MANAGE_TOKEN }}
    working-dir: ${{ matrix.app.working_dir }}
```

Set up Go (with its cache) before this step — the action only fetches; it does not install a toolchain.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `go-private-modules` | `GOPRIVATE` pattern (e.g. `github.com/LerianStudio/*`). Empty skips the prefetch entirely. | No | `''` |
| `manage-token` | Token authorised to read the private modules. | No | `''` |
| `working-dir` | Directory the targets will run from. | No | `'.'` |

## Which modules get fetched

**At or below `working-dir`:** every `go.mod` the Go tool itself would walk — `vendor`, `testdata` and `_`/`.`-prefixed directories are pruned. A Makefile target may drive nested modules or a workspace, and once the step ends there is no credential left to fetch with.

**Enclosing `working-dir`:** when the directory holds no `go.mod` of its own, the nearest `go.mod` above it is the module the targets resolve, so it is fetched too. This is the one-module-at-the-root layout — a repository whose apps live under `components/<app>` as packages of a single module.

The upward walk is bounded by a prefix test on paths resolved with `pwd -P`, not by string equality against `GITHUB_WORKSPACE`: a symlinked workspace, or a self-hosted runner spelling the path differently, would never match an equality test and the walk would climb past the repository. Outside a runner `GITHUB_WORKSPACE` is unset, so the ceiling falls back to the git worktree root and, failing that, the walk is skipped — running this locally or under `act` must not abort it.

## Failure policy

| Module | On `go mod download` failure |
|--------|------------------------------|
| At `working-dir`, or the enclosing one | **Fatal.** It is the module being analysed; nothing downstream can succeed. The error names its absolute path. |
| Nested below `working-dir` | **Warning**, job continues. Those directories hold fixtures, some broken on purpose; if a target really needs one, that target fails with its own, more useful error. |

## Caveat

A Makefile target that resolves a *new* private dependency on its own (`go get`, or `go mod tidy` reaching the network) fails, because by then there is no credential. Declare dependencies in `go.mod` so the prefetch covers them.
