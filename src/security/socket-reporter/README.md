<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>socket-reporter</h1></td>
  </tr>
</table>

Composite action that posts Socket supply-chain **findings** as a single upserted pull request comment.

## Findings only

Whether the scan ran, which App checks passed, and how many alerts were filtered out are operational facts. They belong in the job log and in the `Socket` status check, not in a comment people are asked to read. An earlier version led with a Stage/Status/Blocking table reporting `✅ Clean` for each layer — accurate, and pure noise on the overwhelming majority of pull requests.

What that means concretely:

| Not in the comment | Where it lives |
|---|---|
| "Socket Firewall allowed every package" | Job log |
| App check conclusions | The App's own checks |
| "42 of 4636 alerts carry an action" | Job log |
| An unparsed request (`parseFail`) — a coverage gap | Job log warning |
| App verdict `inconclusive` / `missing` | Job log + the `Socket` check going red |

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `github-token` | Token used to post the comment | **Yes** | — |
| `app-name` | Name in the heading and the comment marker | **Yes** | — |
| `comment-when` | `findings` posts only when there is something to act on; `always` posts every run | No | `findings` |
| `firewall-blocked` | `true` when Socket Firewall refused a package | No | `false` |
| `firewall-fail-on-block` | Whether a block is blocking for this repository | No | `true` |
| `firewall-findings-file` | Socket Firewall report JSON (`blocked[]`, `parseFail[]`) | No | `''` |
| `api-findings-file` | JSON from [`socket-api-report`](../socket-api-report/README.md) | No | `''` |
| `api-blocking-count` | Introduced findings matching the blocking policy | No | `0` |
| `run-url` | Workflow run, linked in the footer | No | `''` |

## Outputs

| Output | Description |
|---|---|
| `has-findings` | `true` when any layer reported a finding, blocking or not |
| `posted` | `true` when a comment was created or updated |

## Shape of the comment

```
## 🛡️ Socket Supply Chain — `app`

### ❌ 2 blocking finding(s) introduced        ← or ⚠️ introduced, none blocking
                                              ← or ✅ No new findings in this pull request

### Refused at install                        ← only when the firewall blocked
| Package | Version | Registry | Findings |

### Introduced by this pull request           ← only when the diff attributes something
🟠 2 warn · 🟡 1 monitor — across 3 package(s)
| Package | Version | Reached via | Score | Findings |
▶ Suggested fixes (3)

---
### Existing tree debt                        ← collapsed, never blocking
▶ Show the 43 pre-existing finding(s)

---
🔍 What this PR changed · Socket scan for `272b8f9` · Workflow logs
```

Three header states, because the middle one used to swallow the good case: a pull request that introduces nothing and only inherits debt is a **pass**, and marking it `⚠️` trains people to ignore the warning that matters.

**Reached via** names the direct dependency that pulls a transitive finding in. `oauth@0.9.15` is nobody's decision — `next-auth` is. Direct dependencies keep `direct, prod`; anything Socket gave no ancestors for falls back to the plain scope.

**Existing tree debt** is collapsed and never gates. It is identical on every pull request in the repository, so promoting it would drown the part this change is responsible for. Each section carries an action breakdown before the collapsed table, so a reader can judge the scale without expanding.

**Suggested fixes** are rendered for both sections. Identical remedies are listed once — one advisory reaches several packages, so the raw list repeats the same `npx socket fix --id`.

## Its own comment, on purpose

The marker is `<!-- socket-supply-chain-<app-name> -->`, distinct from `pr-security-reporter`'s `<!-- security-scan-<app-name> -->`. Two markers means two comments that upsert independently and never contend for the same body.

Folding the Socket rows into the security comment is not reachable: `pr-security-reporter` runs inside the `security_scan` job of `pr-security-scan.yml`, while the Socket layers run in a separate, parallel job. Step outputs do not cross jobs, so merging them would mean moving the Socket steps into a pipeline shared with Go repositories that have no npm install to guard.

It also does not replace the **Socket App's** comment, which stays useful and is not duplicated here: the App shows version transitions and score deltas for changed direct dependencies (`@types/lodash@4.17.24 ⏵ 4.17.25`, Quality `+1`). This action shows action, severity, remediation and provenance. Two different questions.

> The App's comment is one of the inputs `socket-api-report` uses to resolve its diff scan, so disabling it narrows attribution to the commits Socket has already diffed.

## Stale comments

With `comment-when: findings` (the default), nothing is posted when there is nothing to act on. If a previous run **did** report findings and they are now gone, the existing comment is collapsed to a resolved note rather than left in place — a stale body keeps showing fixed findings as current. It is updated, not deleted, so the history stays auditable.

## Usage

### As a composite step

Both upstream steps need `continue-on-error: true` so the report stays reachable when a layer fails, with the verdict re-applied by a gate step afterwards:

```yaml
jobs:
  socket:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    permissions:
      contents: read
      issues: write
      pull-requests: write
    steps:
      - id: firewall
        continue-on-error: true
        uses: LerianStudio/github-actions-shared-workflows/src/security/socket-firewall@v1

      - id: api-report
        continue-on-error: true
        uses: LerianStudio/github-actions-shared-workflows/src/security/socket-api-report@v1
        with:
          socket-api-key: ${{ secrets.SOCKET_SECURITY_API_KEY }}
          report-url: ${{ steps.app-gate.outputs.report-url }}

      - name: Post Socket findings to PR
        if: always()
        uses: LerianStudio/github-actions-shared-workflows/src/security/socket-reporter@v1
        with:
          github-token: ${{ github.token }}
          app-name: ${{ github.event.repository.name }}
          firewall-blocked: ${{ steps.firewall.outputs.blocked || 'false' }}
          firewall-findings-file: ${{ steps.firewall.outputs.findings-file }}
          api-findings-file: ${{ steps.api-report.outputs.findings-file }}
          api-blocking-count: ${{ steps.api-report.outputs.blocking-count || '0' }}
```

### Via the reusable workflow

Wired into the `socket` job of `js-pr-validation`. Skipped when `dry_run: true`, since posting a comment is exactly the side effect a dry run must not have.

```yaml
jobs:
  pr-validation:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/js-pr-validation.yml@v1.x.x
    with:
      socket_comment_when: 'findings'   # default; 'always' posts every run
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
| [`actions/github-script`](https://github.com/actions/github-script) | Builds the comment and upserts it through the authenticated Octokit client, matching how `pr-security-reporter` posts its own. Pinned by commit SHA (`v8`). `result-encoding: string` is required — without it the action JSON-encodes the returned string and the output arrives quoted. |
