<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>socket-reporter</h1></td>
  </tr>
</table>

Composite action that posts the Socket supply-chain results as a single upserted pull request comment, in the same `Stage | Status | Blocking?` layout as [`pr-security-reporter`](../pr-security-reporter/README.md), plus a section per layer.

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `github-token` | Token used to post the comment | **Yes** | — |
| `app-name` | Name shown in the heading and used in the comment marker | **Yes** | — |
| `firewall-enabled` | Whether the Socket Firewall layer ran | No | `true` |
| `firewall-blocked` | `true` when Socket Firewall blocked a package | No | `false` |
| `firewall-exit-code` | Exit code returned by the guarded install | No | `0` |
| `firewall-fail-on-block` | Whether a block is blocking for this repository | No | `true` |
| `guarded-install-count` | How many analysis jobs installed through the firewall, for the coverage line | No | `''` |
| `app-gate-enabled` | Whether the Socket App gate ran | No | `true` |
| `app-findings-file` | Path to the JSON verdict written by [`socket-app-gate`](../socket-app-gate/README.md) | No | `''` |
| `app-fail-on-findings` | Whether an adverse App verdict is blocking for this repository | No | `true` |
| `run-url` | Link to the workflow run, shown in the footer | No | `''` |

## Outputs

| Output | Description |
|---|---|
| `has-findings` | `true` when any layer reported a **blocking** finding |

## Its own comment, on purpose

The marker is `<!-- socket-supply-chain-<app-name> -->`, distinct from `pr-security-reporter`'s `<!-- security-scan-<app-name> -->`. Two markers means two comments that each upsert independently and never contend for the same body.

Folding the Socket rows into the existing security comment would have been the tidier outcome, but it is not reachable: `pr-security-reporter` runs inside the `security_scan` job of `pr-security-scan.yml`, while the Socket layers run in a separate, parallel job of `js-pr-validation.yml`. Step outputs do not cross jobs, so merging them would mean moving the Socket steps into the security pipeline — which is shared with Go repositories that have no npm install to guard.

## Status vocabulary

`has-findings` is only `true` when a finding is **blocking** for this repository. An adverse result under `fail-on-block: false` or `fail-on-findings: false` is rendered with `Blocking? = No` and does not set the output, which keeps the comment honest about what actually gates the merge.

| Layer | Status | Blocking? |
|---|---|---|
| Socket Firewall | `✅ Clean` / `🚫 Package blocked` / `⚠️ Install failed` / `⏭ Disabled` | Per `firewall-fail-on-block` |
| Socket App Alerts | `✅ Clean` / `🚫 Alerts reported` / `⚠️ No verdict reached` / `⏭ App not installed` / `⏭ Disabled` | Per `app-fail-on-findings` |

An install that failed for an ordinary reason (exit code non-zero, no Socket block marker) is reported as `⚠️ Install failed` and is always blocking — it is not a supply-chain finding, but it is not a pass either.

## Usage

### As a composite step

Both upstream steps need `continue-on-error: true` so the report is still reachable when a layer fails, with the verdict re-applied by a gate step afterwards:

```yaml
jobs:
  socket:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    permissions:
      contents: read
      checks: read
      issues: write
      pull-requests: write
    steps:
      - uses: actions/checkout@v6
        with:
          persist-credentials: false

      - id: firewall
        continue-on-error: true
        uses: LerianStudio/github-actions-shared-workflows/src/security/socket-firewall@v1

      - id: app-gate
        continue-on-error: true
        uses: LerianStudio/github-actions-shared-workflows/src/security/socket-app-gate@v1
        with:
          github-token: ${{ github.token }}
          commit-sha: ${{ github.event.pull_request.head.sha }}

      - name: Post Socket report to PR
        if: always()
        uses: LerianStudio/github-actions-shared-workflows/src/security/socket-reporter@v1
        with:
          github-token: ${{ github.token }}
          app-name: ${{ github.event.repository.name }}
          firewall-blocked: ${{ steps.firewall.outputs.blocked || 'false' }}
          firewall-exit-code: ${{ steps.firewall.outputs.install-exit-code || '0' }}
          app-findings-file: ${{ steps.app-gate.outputs.findings-file }}
```

### Via the reusable workflow

Wired into the `socket` job of `js-pr-validation` and posted automatically on pull requests. It is skipped when `dry_run: true`, since posting a comment is exactly the kind of side effect a dry run must not have.

```yaml
jobs:
  pr-validation:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/js-pr-validation.yml@v1.x.x
    secrets: inherit
```

## Permissions required

```yaml
permissions:
  issues: write
  pull-requests: write
```

## Third-party actions used

| Action | Why |
|---|---|
| [`actions/github-script`](https://github.com/actions/github-script) | Builds the comment and upserts it through the authenticated Octokit client, matching how `pr-security-reporter` posts its own comment. Pinned by commit SHA (`v8`). |
