<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>Breaking Change Guard</h1></td>
  </tr>
</table>

Composite action that detects breaking-change commits in a pull request and checks
whether the pull request description contains the required approval acknowledgement.
The action reports detection and approval separately. The caller decides whether to
block the merge.

## Behavior

The guard scans only commits that are in the pull request head and not in the remote
base branch. It uses `origin/<base>..HEAD`, requires a checkout with full history, and
rejects shallow repositories before scanning.

A commit is breaking when either condition is true:

- Its subject matches the pinned parser pattern `^(\w*)(?:\((.*)\))?!: (.*)$`.
  The type uses ASCII word characters and can be empty. The optional scope is
  arbitrary, including nested parentheses. One space after the colon is required;
  the captured description can be empty or start with additional whitespace.
- A commit-message line matches the pinned note grammar: optional leading whitespace,
  `*`, or `|`; then `BREAKING CHANGE` or `BREAKING CHANGES`; then one or more colon or
  whitespace separators. Matching is case-insensitive. `-` bullets and
  `BREAKING-CHANGE` are not accepted by the configured release parser.

Ordinary prose that contains a reserved footer token later in a line is not breaking.
The acknowledgement supports two matching modes:

- `contains` preserves the original direct-action behavior. The acknowledgement is a
  case-sensitive, exact literal substring of the pull request body. It can span
  multiple lines and can contain regular-expression or shell metacharacters.
- `exact-visible-line` requires one visible line to equal the acknowledgement exactly.
  Matching is case-sensitive and rejects leading or trailing whitespace, quoted text,
  and prose that only contains the acknowledgement. Exact lines inside inline or
  multiline HTML comments or Markdown fenced code blocks are ignored. Fences can be
  indented and must open with at least three backticks or three tildes. A closing fence
  must use the same character and be at least as long as its opening fence. Opening
  fences can include a language suffix. A terminal carriage return is removed before
  comparison so CRLF pull request bodies remain valid.

An empty acknowledgement is never approved. An empty or unknown matching mode fails
closed.

The guard fails closed when the repository is shallow, the remote base ref or `HEAD`
is invalid, or Git cannot read the commit range. An unapproved breaking change is a
valid detection result, so the composite exits successfully and leaves enforcement to
its caller.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `base-ref` | Pull request base branch. The checkout must contain `origin/<base-ref>`. | Yes | — |
| `breaking-change-acknowledgement` | Exact string used to approve the breaking change. | Yes | — |
| `acknowledgement-match-mode` | Internal matching mode: `contains` or `exact-visible-line`. | No | `contains` |

The composite has no `dry-run` input. Detection has no side effects. The reusable
workflow owns comment, label, and merge-enforcement controls.

## Outputs

| Output | Description |
|--------|-------------|
| `has-breaking-changes` | `true` when at least one pull request head commit is breaking. |
| `approved` | `true` when the pull request body satisfies the selected acknowledgement matching mode. |

## Why `actions/checkout`

Every example below uses the third-party `actions/checkout` action (pinned by commit
SHA) with `fetch-depth: 0`. The guard reads Git history directly, so the checkout must
materialize `HEAD` and fetch the full history required to resolve
`origin/<base-ref>..HEAD`. A shallow clone makes the guard fail closed.

## Local composite usage

Local paths resolve in the caller repository. Use this form only in this repository
when testing changes to the composite itself.

```yaml
name: Test Breaking Change Guard

on:
  pull_request:

permissions:
  contents: read

jobs:
  breaking-change-guard:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - name: Check out full history
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v6
        with:
          fetch-depth: 0

      - name: Detect breaking changes
        id: guard
        uses: ./src/validate/breaking-change-guard
        with:
          base-ref: ${{ github.base_ref }}
          breaking-change-acknowledgement: >-
            Breaking change approved: this PR intentionally ships a breaking change;
            the next release will be a major version bump.

      - name: Enforce approval
        if: steps.guard.outputs.has-breaking-changes == 'true' && steps.guard.outputs.approved != 'true'
        run: exit 1
```

## Pre-release testing

Use `@develop` only to test the composite before it is published in `v1`:

```yaml
jobs:
  breaking-change-guard:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v6
        with:
          fetch-depth: 0
      - id: guard
        uses: LerianStudio/github-actions-shared-workflows/src/validate/breaking-change-guard@develop
        with:
          base-ref: ${{ github.base_ref }}
          breaking-change-acknowledgement: Breaking change approved by the release owner.
```

Do not use a branch reference in production.

## Production usage after release

After the release publishes this composite in `v1`, use the stable major tag:

```yaml
jobs:
  breaking-change-guard:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v6
        with:
          fetch-depth: 0
      - id: guard
        uses: LerianStudio/github-actions-shared-workflows/src/validate/breaking-change-guard@v1
        with:
          base-ref: ${{ github.base_ref }}
          breaking-change-acknowledgement: Breaking change approved by the release owner.
```

Mandatory `pr-validation` integration always uses `exact-visible-line`. The workflow
does not expose the matching mode as an opt-out or configuration input. Direct
composite callers retain `contains` by default and can select `exact-visible-line`
explicitly when they need the same strict acknowledgement contract.

## Local test

Run the durable detector and mandatory workflow-integration suites from the repository
root:

```bash
bash src/validate/breaking-change-guard/test.sh
python3 src/validate/breaking-change-guard/test-workflow.py
```

The detector test always runs with the default `awk`. It also runs the complete matrix
with GNU `awk` when `gawk` is installed. The workflow test executes the Bash bodies
from `.github/workflows/pr-validation.yml` directly and verifies the mandatory guard
wiring across the reusable, umbrella, reporting, summary, and self-validation
workflows.
