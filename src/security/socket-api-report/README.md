<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>socket-api-report</h1></td>
  </tr>
</table>

Composite action that reads the full scan the [Socket GitHub App](https://github.com/marketplace/socket-security) already computed and extracts per-package alerts, vulnerabilities and scores for reporting.

This is the only layer that can answer *"what is wrong with which package"*. The other two cannot, by construction:

- **Socket Firewall free** reports what it **refused**, never an assessment of what it allowed. Its JSON report is `{blocked, parseFail}` — nothing about the packages that passed.
- **The App's check runs** carry a status and a link. `Project Report`'s `output.text` is `null`; the detail lives on the dashboard, not in the check.

## How it avoids a second scan

The App publishes its result as a dashboard URL:

```
https://socket.dev/dashboard/org/<org-slug>/sbom/<full-scan-id>
```

Both identifiers are parsed from it, then the scan is read back through `GET /v0/orgs/{org}/full-scans/{id}`. Nothing is re-analysed and no scan is created — one quota unit for the read. Creating a scan with `socketcli` would have duplicated work the App had already done and produced a competing report.

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `socket-api-key` | Socket API token. Empty skips with a notice | No | `''` |
| `report-url` | Dashboard URL of the scan, as exposed by [`socket-app-gate`](../socket-app-gate/README.md)'s `report-url` output | No | `''` |
| `org-slug` | Overrides the org slug parsed from `report-url` | No | `''` |
| `full-scan-id` | Overrides the scan id parsed from `report-url` | No | `''` |
| `max-rows` | Maximum package rows kept, most-flagged first | No | `25` |
| `findings-file` | Path where the extracted JSON is written for `socket-reporter` | No | `socket-api-findings.json` |
| `debug-sample` | Log the artifact keys and one alert object, to adapt to an API change | No | `false` |

## Outputs

| Output | Description |
|---|---|
| `skipped` | `true` when nothing was produced (no token, no resolvable scan id, or an API error) |
| `findings-file` | Path to the extracted findings JSON |
| `alert-count` | Total alerts across all artifacts in the scan |

## Token scope

`full-scans:list` is the documented requirement for `GET /v0/orgs/{org}/full-scans/{id}`. Grant nothing else — this action only reads.

HTTP failures are classified rather than lumped together, because they call for different fixes:

| Status | Reported as |
|---|---|
| `401` | Token invalid or revoked |
| `403` | Token missing the `full-scans:list` scope |
| `404` | Scan not found under that org |
| `429` | Quota or rate limit exhausted |

## Advisory by construction

Every failure path exits `0`. This action **never** gates a merge: enforcement belongs to [`socket-app-gate`](../socket-app-gate/README.md), which turns the App's verdict into a status check, and to [`setup-node-guarded`](../../setup/setup-node-guarded/README.md), which refuses the install outright. A reporting layer that could fail the build would make a Socket outage or an exhausted quota look like a security finding.

## Extracted shape

```json
{
  "scanScores":    { "overall": 0.77, "supplyChain": 0.81, "vulnerability": 0.55 },
  "artifactCount": 1986,
  "flaggedCount":  12,
  "alertCount":    31,
  "alertsByType":  [ { "type": "cve", "count": 9 } ],
  "packages":      [ { "name": "@scope/widget", "version": "2.0.0", "direct": false,
                       "dev": true, "scores": {},
                       "alerts": [ { "type": "installScript", "severity": "middle",
                                     "category": "supplyChainRisk" } ],
                       "alertCount": 1 } ],
  "truncated":     false
}
```

Alert objects are read defensively — `type` is the documented key, with `key` and `alert` accepted as fallbacks so a field rename upstream degrades to a label instead of an empty report. Use `debug-sample: true` to log the real artifact keys when adapting.

## Usage

### As a composite step

```yaml
- id: app-gate
  uses: LerianStudio/github-actions-shared-workflows/src/security/socket-app-gate@v1
  with:
    github-token: ${{ github.token }}
    commit-sha: ${{ github.event.pull_request.head.sha }}

- id: api-report
  continue-on-error: true
  uses: LerianStudio/github-actions-shared-workflows/src/security/socket-api-report@v1
  with:
    socket-api-key: ${{ secrets.SOCKET_SECURITY_API_KEY }}
    report-url: ${{ steps.app-gate.outputs.report-url }}
```

It reads `report-url` from the gate, so the gate must run first.

### Via the reusable workflow

```yaml
jobs:
  pr-validation:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/js-pr-validation.yml@v1.x.x
    with:
      socket_enable_api_report: true   # default
      socket_api_max_rows: 25          # default
    secrets: inherit                   # carries SOCKET_SECURITY_API_KEY
```

## Permissions required

```yaml
permissions:
  contents: read
```

No GitHub scope beyond checkout — it talks to the Socket API, not to GitHub.

## Third-party actions used

None. It uses the preinstalled `curl` and `jq`. The token is passed through a `curl --config` file rather than the command line, so it never appears in the process table of a shared runner.
