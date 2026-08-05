<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>socket-app-gate</h1></td>
  </tr>
</table>

Composite action that waits for the [Socket Security GitHub App](https://github.com/marketplace/socket-security) check runs on a commit and turns their conclusions into a verdict the workflow controls.

The App already does the dependency-graph analysis and posts `Socket Security: Project Report` and `Socket Security: Pull Request Alerts`. What it does not do is **enforce**: its checks land as `success`, `neutral` or `skipped`, and neither `neutral` nor `skipped` blocks a pull request under branch protection. This action closes that gap without duplicating the analysis, without an API token and without consuming Socket quota — the alternative, running `socketcli` in CI, would re-scan the same dependency graph and post a second, competing report.

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `github-token` | Token used to read check runs on the commit | **Yes** | — |
| `commit-sha` | Commit whose check runs are inspected. Must be the PR **head** SHA, not the merge SHA | **Yes** | — |
| `app-slug` | GitHub App slug that owns the checks | No | `socket-security` |
| `timeout-seconds` | How long to wait for the checks to complete | No | `300` |
| `poll-interval-seconds` | Delay between polls | No | `15` |
| `fail-on-findings` | Fail when a check concludes adversely | No | `true` |
| `on-inconclusive` | `block` or `warn` when the App reached no verdict | No | `block` |
| `on-missing-app` | `warn` or `block` when the App published no checks at all | No | `warn` |
| `findings-file` | Path where the JSON verdict is written for `socket-reporter` | No | `socket-app-findings.json` |

## Outputs

| Output | Description |
|---|---|
| `verdict` | `pass` \| `findings` \| `inconclusive` \| `missing` |
| `report-url` | Link to the Socket dashboard report, when a check exposed one |
| `findings-file` | Path to the JSON verdict file |

## The four verdicts

| Verdict | When | Default behaviour |
|---|---|---|
| `pass` | Every App check completed with a non-adverse conclusion | Passes |
| `findings` | A check concluded `failure`, `action_required`, `cancelled` or `timed_out` | **Fails** (`fail-on-findings`) |
| `inconclusive` | Checks exist but concluded `neutral`/`skipped`, or the wait timed out | **Fails** (`on-inconclusive`) |
| `missing` | The App published no checks on this commit | Warns (`on-missing-app`) |

`inconclusive` and `missing` are deliberately separate. They look similar and mean opposite things:

- **`inconclusive`** is the App declining to judge. On a pull request with merge conflicts the `Pull Request Alerts` check reports *"Skipped un-mergeable pull request"* — no diff against the target branch was analysed at all. Treating that as clean would let exactly the wrong pull request through, so the default blocks and names the likely cause.
- **`missing`** is simply a repository without the App installed. Blocking there would break every such repository for a reason its authors cannot act on, so the default warns and relies on install-time protection from [`setup-node-guarded`](../../setup/setup-node-guarded/README.md).

## Why it polls

The App publishes its checks asynchronously, so this job routinely starts before they exist. The action polls until every check owned by `app-slug` has completed, or until `timeout-seconds`. A timeout is classified as `inconclusive` — never as success.

## Usage

### As a composite step

```yaml
jobs:
  socket:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    permissions:
      contents: read
      checks: read
    steps:
      - name: Socket App Gate
        id: app-gate
        uses: LerianStudio/github-actions-shared-workflows/src/security/socket-app-gate@v1
        with:
          github-token: ${{ github.token }}
          commit-sha: ${{ github.event.pull_request.head.sha }}
```

`commit-sha` must be the head SHA: for a `pull_request` event `github.sha` is the merge commit, which carries no App checks.

### Via the reusable workflow

```yaml
jobs:
  pr-validation:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/js-pr-validation.yml@v1.x.x
    with:
      socket_enable_app_gate: true              # default
      socket_app_on_inconclusive: 'block'       # default
      socket_app_on_missing: 'warn'             # default
    secrets: inherit
```

## Permissions required

```yaml
permissions:
  contents: read
  checks: read
```

## Third-party actions used

None. The action calls the GitHub REST check-runs API through the preinstalled `gh` CLI, so there is no dependency to pin.
