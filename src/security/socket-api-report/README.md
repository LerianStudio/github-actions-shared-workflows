<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>socket-api-report</h1></td>
  </tr>
</table>

Composite action that reads the Socket scan for a commit and separates the dependency findings **this pull request introduces** from the debt the tree already carried.

It is the only layer that can answer *"what is wrong with which package, and is it ours"*. The other two cannot, by construction:

- **Socket Firewall free** reports what it **refused**. Its JSON is `{blocked, parseFail}` — silent about everything that passed.
- **The App's check runs** carry a status and a link. `Project Report`'s `output.text` is `null`; the detail lives on the dashboard.

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `socket-api-key` | Socket API token. Empty skips with a notice | No | `''` |
| `report-url` | Dashboard URL of the scan, from [`socket-app-gate`](../socket-app-gate/README.md)'s `report-url`. The org slug and scan id are parsed from it | No | `''` |
| `org-slug` | Overrides the org slug parsed from `report-url` | No | `''` |
| `full-scan-id` | Overrides the scan id parsed from `report-url` | No | `''` |
| `diff-scan-id` | Socket diff scan id for this pull request. See [Attribution](#attribution) | No | `''` |
| `base-branch` | Target branch, reported as the comparison point | No | `''` |
| `head-sha` | Head commit, used to label the scan link | No | `''` |
| `include-actions` | Alert actions treated as findings | No | `error,warn,monitor` |
| `fail-on-actions` | Actions that make an **introduced** finding blocking. Empty blocks nothing | No | `''` |
| `max-rows` | Maximum package rows kept per section | No | `25` |
| `findings-file` | Path where the extracted JSON is written for `socket-reporter` | No | `socket-api-findings.json` |
| `debug-sample` | Log the alert object shape, for adapting to an API change | No | `false` |

## Outputs

| Output | Description |
|---|---|
| `skipped` | `true` when nothing was produced (no token, no resolvable scan, or an API error) |
| `findings-file` | Path to the extracted findings JSON |
| `introduced-count` | Actioned findings this pull request introduces |
| `preexisting-count` | Actioned findings already present on the target branch |
| `blocking-count` | Introduced findings matching `fail-on-actions`. Zero when it is empty |

## Filtering: why 4636 alerts become 42

Measured on a real 1897-artifact tree, alert actions came back as `ignore` 4594, `monitor` 24, `warn` 18. Reporting unfiltered rendered the same `envVars` hundreds of times in a single table cell — technically complete, unreadable.

**Severity is not a usable filter**: 118 alerts were `high` and still `ignore`d. Action is the axis Socket's own dashboard filters on, so it is the axis used here.

Capabilities like `envVars`, `networkAccess` and `filesystemAccess` are marked `ignore` because in isolation they are normal — an HTTP client reads the proxy from the environment. Hostility is a combination, and Socket has already made that judgement by the time it assigns an action.

Repeats are collapsed per package and alert type into a count with the first file, since an alert fires once per source location.

## Attribution

`fail-on-actions` applies **only to introduced findings**. Gating on inherited debt fails every pull request in a repository for something none of them caused, and the gate gets switched off in its first week.

Attribution comes from Socket's own diff scan. Two home-grown baselines failed first, and both failures are worth knowing:

1. Comparing against the newest full scan of the target branch produced **38 false attributions** on a change that touched a single types package.
2. Filtering candidates by `scan_state` rejected all ten. Every scan in this organization persists as `pending` or `resolve` — the head scan included, whose data is demonstrably complete. **`scan_state` carries no completion meaning here.**

Measuring package overlap then showed why no baseline was usable: the newest target-branch scan shared only **31.8%** of the head tree's `package@version` set despite holding 82% as many artifacts. An artifact-count threshold would have accepted it — which is exactly how the 38 false attributions happened.

So the diff is read, not approximated. `added`, `updated` and `replaced` define what the pull request is responsible for; `updated` and `replaced` count because a version or source change makes those findings this change's problem too.

The diff is resolved in three steps, in this order:

1. **Look the diff up by `after_full_scan_id`**, keyed on the scan for this commit. When Socket has already diffed that exact scan, this is authoritative and nothing else runs.
2. **Fall back to the id in the App's comment** (`diff-scan-id`). It is used only as a hint: its *before* side is read and a fresh diff is built against this commit's scan via `POST diff-scans/from-ids`. The App diffs against a different full scan than the one its `Project Report` check links to, so its published id is frequently keyed on the wrong *after* side — reusing it directly would attribute against a tree that is not this one.
3. **Otherwise, no attribution.** Everything is reported as pre-existing.

Step 2 is the only place a third-party bot's comment is involved, and it is degradable: with the App's comments disabled, step 1 still resolves whenever Socket has diffed this scan.

Without a diff scan nothing is attributed and everything is reported as pre-existing. No attribution is honest; a confident wrong one is not.

## The blame chain

A transitive finding is not actionable on its own — nobody installed `brace-expansion` on purpose. `topLevelAncestors` carries artifact **references**, so an id-to-name map is built from the same scan and resolved through it, turning a row into `via eslint, jest +1`.

Measured coverage on the reference tree: **1755 of 1897** artifacts carry the field, and all 1897 ids resolve. The remainder are direct dependencies, which have no ancestor by definition.

## Token scopes

| Scope | For |
|---|---|
| `full-scans:list` | Reading the scan for the commit |
| `diff-scans:list` | Reading the diff scan that drives attribution |
| `diff-scans:create` | Rebuilding the diff when the App's published id is keyed on another scan |

Grant nothing else. The single write is that rebuilt diff scan; `on_duplicate=redirect` makes reruns idempotent rather than creating one per run.

## Why this does not use curl

`api.socket.dev` sits behind Cloudflare, which **fingerprints the HTTP client**. `curl` is answered with a managed challenge — `403`, an HTML interstitial, `cf-mitigated: challenge` — which by status code alone is indistinguishable from a scope denial and sends you auditing token permissions that were never the cause.

Reproduced with `Authorization: Bearer`, with HTTP Basic, with a custom User-Agent, with the exact header shape `socket-sdk-python` sends, on `/v0/quota` as well as the full-scan endpoint, from a developer machine and a Blacksmith runner, three spaced retries each.

Python's stdlib client is not challenged. It is also the stack the official SDK uses, and the reason `sfw` reaches Socket from the very runner where `curl` is blocked. The `cf-mitigated` check is kept as a regression guard.

## Advisory by construction

Every failure path exits `0`, and HTTP statuses are classified separately (`401` invalid, `403` missing scope, `404` wrong scan, `429` quota, plus the Cloudflare case) because they need different fixes. Only real findings can block: a Socket outage or an exhausted quota must never read as a security finding.

## Extracted shape

```json
{
  "orgSlug": "lerian",
  "scanId": "26e58204-…",
  "headSha": "272b8f9…",
  "diffScanId": "05460112-…",
  "hasBaseline": true,
  "baseBranch": "develop",
  "artifactCount": 1897,
  "alertCountRaw": 4636,
  "includedActions": ["error", "monitor", "warn"],
  "introducedCount": 0,
  "preexistingCount": 43,
  "alertsByType": [{ "type": "obfuscatedFile", "action": "warn", "count": 17 }],
  "introduced": [],
  "preexisting": [
    {
      "name": "oauth", "version": "0.9.15",
      "artifactId": 51509, "ancestors": ["next-auth@4.24.15"],
      "direct": false, "dev": false, "overallScore": 0.8,
      "worstAction": "warn", "worstSeverity": "high",
      "findings": [{ "type": "obfuscatedFile", "action": "warn", "severity": "high",
                     "category": "supplyChainRisk", "count": 1,
                     "file": "dist/oauth.js", "fix": null }]
    }
  ],
  "introducedTruncated": false,
  "preexistingHidden": 18,
  "preexistingHiddenFindings": 24
}
```

Alert objects carry `action`, `actionSource`, `category`, `severity`, `type`, `key`, `file`, `start`, `end`, `fix` — verified against a real scan. `fix` is an **object**, not a string. Use `debug-sample: true` to log the real shape when adapting.

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
    diff-scan-id: ${{ steps.diff-scan.outputs.id }}
    base-branch: ${{ github.base_ref }}
    head-sha: ${{ github.event.pull_request.head.sha }}
```

It reads `report-url` from the gate, so the gate must run first.

### Via the reusable workflow

```yaml
jobs:
  pr-validation:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/js-pr-validation.yml@v1.x.x
    with:
      socket_enable_api_report: true                    # default
      socket_api_include_actions: 'error,warn,monitor'  # default
      socket_api_fail_on_actions: 'error'               # default '' — blocks nothing
    secrets: inherit                                    # carries SOCKET_SECURITY_API_KEY
```

## Permissions required

```yaml
permissions:
  contents: read
```

No GitHub scope beyond checkout — it talks to the Socket API, not to GitHub.

## Third-party actions used

None. It uses the preinstalled `python3` (stdlib only, no `pip install`) and `jq`. The token is read from the environment inside the Python process, never passed as an argument, so it never appears in the process table of a shared runner.
