<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>socket-scan</h1></td>
  </tr>
</table>

Composite action that runs the [Socket CLI](https://docs.socket.dev/docs/socket-cli) (`socketcli`) against the repository's dependency manifests. It produces a full supply-chain report, comments the alerts on the pull request and enforces the organization's Socket policy.

This is the paid tier of Socket and needs an API token. Without one the action **skips with a notice** instead of failing, so it can be wired into a shared workflow before any account exists. For the free, token-less layer that blocks malicious packages at install time, see [`socket-firewall`](../socket-firewall/README.md).

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `socket-api-key` | Socket API token. Empty skips the scan with a notice | No | `''` |
| `github-token` | Token used by `socketcli` to post the alert report on the pull request | No | `''` |
| `target-path` | Directory scanned for dependency manifests | No | `.` |
| `pr-number` | Pull request number reported to Socket. `0` outside a pull request | No | `0` |
| `python-version` | Python version used to run the Socket CLI | No | `3.12` |
| `fail-on-findings` | Fail the step on blocking alerts. When `false` the scan still runs and reports | No | `false` |
| `sarif-file` | Path where the SARIF report is written. Empty skips SARIF generation | No | `''` |
| `ignore-commit-files` | Scan every manifest instead of only the ones touched by the commit | No | `false` |
| `dry-run` | Print the resolved configuration without invoking `socketcli` | No | `false` |

## Outputs

| Output | Description |
|---|---|
| `skipped` | `true` when the scan did not run because no Socket API token was provided |
| `exit-code` | Exit code returned by `socketcli` |
| `sarif-file` | Path to the generated SARIF report. Empty when not requested or never written |

## Exit codes and enforcement

`socketcli` encodes its verdict in the exit code. The action maps it as follows:

| Exit | Meaning | Result |
|---|---|---|
| `0` | No blocking alert | Step passes |
| `1` | Blocking alerts reported | Fails when `fail-on-findings: true`, otherwise `::warning::` |
| `2` | Socket CLI failure | Fails when `fail-on-findings: true`, otherwise `::warning::` |
| `3` | Socket API error | Always `::warning::` — never blocks |
| `5` | Reachability prerequisite unmet | Always `::warning::` — never blocks |

Exit codes `3` and `5` are infrastructure problems: they say nothing about the dependencies under review, so they never block a pull request.

`--disable-blocking` is deliberately **never** passed. It forces exit `0` over everything, including the API failures that normally surface as exit `3`, which would make advisory mode indistinguishable from a clean scan. The native exit code always reaches the evaluation step, and that step is the single place deciding success or failure — so enforcement stays opt-in per repository, the same discipline as `fail_on_coverage_threshold` and the pre-release gate, without losing the signal.

## Dry run

`socketcli` has no native `--dry-run`: any invocation authenticates, creates a real scan on Socket and — with `--scm github` — comments on the pull request. With `dry-run: true` the CLI is therefore **not invoked at all**; only the resolved configuration is printed.

## SARIF

Setting `sarif-file` writes a SARIF report and exposes its path as an output — but only once the file exists on disk, so a scan that failed before writing it reports an empty output rather than a path to a missing file. The action does **not** upload it to the GitHub Security tab: that requires Code Security (GHAS) on the repository, the same reason `codeql_upload_sarif` defaults to `false` in `pr-security-scan`. Consuming workflows that do have GHAS can pipe the output into `github/codeql-action/upload-sarif`.

## Usage

### As a composite step

```yaml
jobs:
  socket:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    permissions:
      contents: read
      issues: write
      pull-requests: write
    env:
      SOCKET_API_KEY: ${{ secrets.SOCKET_SECURITY_API_KEY }}
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 2
          persist-credentials: false

      - name: Socket Scan
        uses: LerianStudio/github-actions-shared-workflows/src/security/socket-scan@v1
        with:
          socket-api-key: ${{ env.SOCKET_API_KEY }}
          github-token: ${{ github.token }}
          pr-number: ${{ github.event.pull_request.number || 0 }}
```

The token is mapped to a job-level `env` var because the `secrets` context is not available in step conditions — the action resolves presence itself and skips when the value is empty.

### Via the reusable workflow

The scan is wired into the `js-pr-validation` umbrella and **disabled by default**:

```yaml
jobs:
  pr-validation:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/js-pr-validation.yml@v1.x.x
    with:
      socket_enable_scan: true          # opt-in
      socket_fail_on_findings: false    # default — advisory first
    secrets: inherit                    # carries SOCKET_SECURITY_API_KEY
```

## Third-party actions used

| Action | Why |
|---|---|
| [`actions/setup-python`](https://github.com/actions/setup-python) | `socketcli` ships as the `socketsecurity` PyPI package — the vendor-documented CI client — so a pinned Python runtime is required. Pinned by commit SHA (`v7`). |

No vendor-provided GitHub Action exists for the Socket CLI, so the composite installs the published package directly. `actions/checkout` is **not** used here: the consuming workflow owns the checkout, because `socketcli` diffs the commit to decide which manifests changed and therefore needs `fetch-depth: 2` — a depth this action cannot impose on a workspace it does not own.

## Permissions required

```yaml
permissions:
  contents: read
  issues: write
  pull-requests: write
```

`issues: write` and `pull-requests: write` are what let `socketcli --scm github` post and update the alert report on the pull request.
