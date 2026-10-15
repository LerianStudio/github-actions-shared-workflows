<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>PR Gate Scope</h1></td>
  </tr>
</table>

> **Unreleased.** Until this ships in a release, reference it as `@develop` —
> `@v1` is the previous release and does not contain it yet.

Decides whether a pull request falls inside a gate's scope, and says why.

Any gate that should apply to some pull requests and not others needs this
decision, and gets it wrong in the same ways: deciding from the event payload
after a retarget, letting a bot's pull request match a positive rule, or
treating a malformed rule set as "nothing in scope" instead of as an error.

## Scope is a base → head mapping

Not two independent dimensions OR'd together — a mapping, because *where a pull
request is landing* is usually the question a gate is really asking:

```json
{"develop": "*", "main": "hotfix/*"}
```

Everything into `develop`; only `hotfix/*` into `main`. A base absent from the
object is never in scope.

`additional-scope-rules` is merged over `scope-rules` key by key: a base present
in both takes the additional value — write the complete pattern set for that
base, not just the addition — and a base present only there is added. That lets a
repository with its own promotion path configure itself without restating the
defaults.

## Order of decision, and it matters

1. **ignored authors** — a veto, before anything else
2. **skip labels** — an explicit opt-out
3. **base → head rules**
4. **force labels** — an explicit opt-in for what the rules missed

The vetoes come first on purpose. Expressed as extra scope dimensions they would
be OR'd with the positive ones and lose to any match — which is exactly how a
"never review release PRs" rule ends up reviewing release PRs.

## Reads the live pull request

Through `gh pr view`, not the event payload, which is frozen at dispatch. A run
started before a retarget would otherwise decide against a base branch that no
longer applies.

## Bot logins have three spellings

REST returns `dependabot[bot]`, GraphQL returns `dependabot`, and
`gh pr view --json author` — what this composite reads — returns
`app/dependabot`, because the CLI prefixes bot logins with `app/`. Both affixes
are stripped from both sides, so all three are the same entry in
`ignore-authors`. Write whichever spelling you last saw.

## Fails closed

A malformed `scope-rules` or `additional-scope-rules` is a non-zero exit, not an
empty rule set. An empty rule set would report `in-scope=false` for everything
and look like a working gate that simply never matches.

A missing or zero `pr-number` is also an error — the composite never guesses from
the event.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `github-token` | Token used to read the pull request. Needs `pull-requests: read`. | Yes | — |
| `pr-number` | Pull request to resolve. | Yes | — |
| `repository` | Repository owning the pull request, as `owner/name`. | No | `${{ github.repository }}` |
| `scope-rules` | JSON object mapping an exact base branch to pipe-separated head globs. | Yes | — |
| `additional-scope-rules` | JSON object merged over `scope-rules`, key by key. | No | `''` |
| `force-labels` | Comma-separated labels that put a pull request in scope regardless of the rules. | No | `''` |
| `skip-labels` | Comma-separated labels that take a pull request out of scope. | No | `''` |
| `ignore-authors` | Comma-separated logins never in scope, checked first as a veto. | No | `''` |
| `verbose` | Print the resolved inputs to the step log. Wire to the caller's `dry_run`. | No | `false` |

Whitespace around commas is tolerated. Labels are matched case-insensitively.

## Outputs

| Output | Description |
|--------|-------------|
| `in-scope` | Whether the pull request is inside the scope (`true`/`false`). |
| `reason` | Why — the matched rule, the label, or what failed to match. |
| `pr-number` | The pull request that was resolved. |
| `base-ref` | Base branch, read live. |
| `head-ref` | Head branch, read live. |
| `head-sha` | Head commit, read live. |
| `author` | Author login, as the CLI spells it. |

`reason` is meant to be surfaced. A gate that blocks without saying which rule
caught the pull request is a gate people route around.

## Usage

```yaml
- name: Resolve the gate scope
  id: scope
  uses: LerianStudio/github-actions-shared-workflows/src/validate/pr-gate-scope@v1
  with:
    github-token: ${{ secrets.MANAGE_TOKEN || github.token }}
    pr-number: ${{ github.event.pull_request.number }}
    scope-rules: '{"develop": "*", "main": "hotfix/*"}'
    ignore-authors: dependabot[bot]

- name: Do the gated work
  if: steps.scope.outputs.in-scope == 'true'
  run: echo "gated via ${{ steps.scope.outputs.reason }}"
```

## Local test

```bash
bash src/validate/pr-gate-scope/test.sh
```

32 cases against a stubbed `gh`: the rules and their globs, the merge semantics
of `additional-scope-rules`, both label overrides and their precedence, the three
bot spellings, and every input that must fail closed. No network, no repository
fixture.
