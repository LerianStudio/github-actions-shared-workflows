<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>breaking-change-approval</h1></td>
  </tr>
</table>

Holds a pull request that carries breaking-change commits until a human has
approved it through the `breaking-approval` Environment, so a major version bump
is always a decision somebody made.

Semantic release reads the commit messages, not the intent behind them. A `!`
typed out of habit, or a `BREAKING CHANGE:` footer pasted from a template, is
enough to push the next release a whole major version — and once it is tagged,
every consumer has to be told what broke, even when nothing did.

This workflow puts a person between the commit and the tag, and asks them one
question: **is this breaking change necessary?**

- **Approving** records that it is, and releases the merge.
- **Rejecting** records that it is not, and **closes the pull request** so the
  change can be reworked without the break.

## Why an Environment

Same mechanism as the tier promotion train. The work stops at a job whose
`environment:` carries required reviewers, the run sits pending until somebody
answers, and **approving resumes the very same run**.

That is what makes the gate practical. A review-based gate has a problem with no
good answer: submitting a review does not re-run a `pull_request` workflow, so
the check goes red when the breaking change is found and stays red after the
approval lands, until somebody re-runs it by hand. An Environment approval has
no such gap — there is no second trigger to arrange, and no `pull_request_review`
anywhere in this workflow.

It also puts the decision where decisions already live: the pending deployment
shows up in the reviewer's own queue, carries an optional comment, and is
recorded in the run's approval log rather than inferred from a review state.

```
detect  →  request          →  approval               →  outcome
           comment + label     Environment: pending      approved → merge released
           + preflight         ⏸ waits for a human       rejected → PR closed
```

## Composition

The workflow orchestrates; the work lives in composites, each reusable on its
own:

| Composite | Responsibility |
|---|---|
| [`pr-gate-scope`](../src/validate/pr-gate-scope/README.md) | Is this pull request in scope, and why — base → head rules, label overrides, author vetoes |
| [`breaking-change-guard`](../src/validate/breaking-change-guard/README.md) | Does the branch carry a breaking-change commit |
| [`codeowners-reviewers`](../src/validate/codeowners-reviewers/README.md) | Who owns this repository, per its CODEOWNERS |
| [`environment-protection`](../src/validate/environment-protection/README.md) | Does `breaking-approval` exist with required reviewers — creating it when it does not |
| [`environment-approvals`](../src/validate/environment-approvals/README.md) | Who approved or rejected, and could we read that at all |
| [`breaking-change-approval-reporter`](../src/notify/breaking-change-approval-reporter/README.md) | The single pull request comment, in each of its states |

What stays in the workflow is the part that is genuinely orchestration: turning
those facts into a verdict, closing the pull request, and failing the check.
`pr-gate-scope` and the two Environment composites were written to be useful to
any future gate, not just this one.

## How it differs from the guard in `pr-validation`

`pr-validation.yml` already runs the same detector, and already blocks. What it
checks is the pull request **body**: the author must paste an exact
acknowledgement line. That records *intent* — and the author is the one person
who cannot be a second opinion on their own change.

| | author acknowledgement | this gate |
|---|---|---|
| Signal | an exact line in the PR body | an Environment approval |
| Who provides it | the author | a required reviewer |
| Scope | every pull request | base → head rules |
| Answers | "did the author mean it?" | "does the team agree it is necessary?" |

They compose, and they share work: when this workflow runs inside
`pr-validation.yml`, the detection is **handed over** rather than repeated — the
guard job already ran the same composite over the same commits, so a second
full-history checkout would buy nothing. The acknowledgement state is shown to
the reviewer as context.

## Setup

### The Environment creates itself, owned by CODEOWNERS

On the first pull request that carries a breaking change, the gate creates
`breaking-approval` — with *Prevent self-review* on, and with the repository's
own **CODEOWNERS** as the required reviewers. There is nothing to prepare and
nothing to keep in sync: the people who own the code are the people asked
whether the break is necessary.

```
.github/CODEOWNERS                       breaking-approval
*  @LerianStudio/g_github_devops   →     required reviewers: g_github_devops
```

CODEOWNERS is read from the pull request's **base** ref. Reading the head would
let an author edit who is allowed to approve their own breaking change.

Pass `breaking_change_approval_reviewers` to override, as comma-separated
`team:<slug>` or `user:<login>`.

Three conditions:

- **`MANAGE_TOKEN` must be able to administer the repository.** Creating an
  Environment needs the `administration` permission, which the default
  `GITHUB_TOKEN` does not have and `permissions:` cannot grant. Without such a
  token the gate fails and names what it needs, rather than running without a
  gate.
- **CODEOWNERS must yield a reviewer.** No file, no `*` rule, or only email
  owners means nothing to create the Environment with — the gate fails rather
  than creating one that approves itself.
- **At most six reviewers.** That is the Environment limit; anything beyond it
  is reported in the log rather than dropped quietly.

To create it by hand instead, pass `breaking_change_create_environment: false`:

```bash
gh api --method PUT repos/<owner>/<repo>/environments/breaking-approval \
  --input - <<'JSON'
{"prevent_self_review": true, "reviewers": [{"type": "Team", "id": <team_id>}]}
JSON
```

> **A missing Environment is not a safe default.** A job referencing one that
> does not exist *creates it, unprotected*, and sails through — a green check
> that gates nothing. That is why the gate either creates a properly protected
> Environment or refuses to run, and never simply proceeds.

### An existing Environment is never rewritten

If `breaking-approval` already exists but has no required reviewers, the gate
**fails and leaves it alone**. A `PUT` replaces the whole configuration, so
repairing it from here would silently drop a wait timer or branch policy
somebody set on purpose. Add the reviewers under Settings → Environments.

### Turn it on

Repositories on `go-pr-validation.yml`, `js-pr-validation.yml` or
`pr-validation.yml` get the gate **by default** — there is nothing to add.

```yaml
with:
  # only if this repository's reviewers differ from the default
  breaking_change_approval_reviewers: 'team:my-team,user:someone'
```

### Make it required

Add **Breaking Change Approval** to the required status checks on the protected
branches. Without that, the red check is advice rather than a gate.

## Standalone usage

For a repository that does not use any of the umbrellas:

```yaml
name: Breaking Change Approval

on:
  pull_request:
    types: [opened, synchronize, reopened, edited, ready_for_review]

permissions:
  contents: read
  pull-requests: write

jobs:
  breaking-change-approval:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/breaking-change-approval.yml@tier-1
    secrets:
      MANAGE_TOKEN: ${{ secrets.MANAGE_TOKEN }}
```

Called this way the workflow detects on its own, with two checkouts: a plain one
for the `origin/<base>` remote-tracking refs, then `refs/pull/<n>/head` with
`clean: false` to move `HEAD` onto the pull request. Nothing from the tree is
executed — only commit messages are read — so fork code never runs.

### Testing before adoption

```yaml
    with:
      dry_run: true
```

`dry_run: true` prints the resolved scope and the detection result, and never
comments, labels, requests an approval or fails. It is how to find out what the
gate would have held over the last few weeks before turning it on.

## Scope

Scope is a **base → head** mapping, because where a breaking change lands is what
decides whether the bump matters:

```json
{"develop": "*", "main": "hotfix/*"}
```

Everything reaching `develop` is gated — that is where the next release is
assembled. On `main` only `hotfix/*` is, because every other source reached
`main` through `develop` and was already gated there. Gating both would ask the
same person the same question twice, which is how a gate becomes something people
click through without reading.

A base absent from the object is never gated.

### The open field

`additional_scope_rules` is the input for the cases the default cannot
anticipate, merged over `scope_rules` key by key:

```yaml
# a repository that promotes through release-candidate
breaking_change_additional_scope_rules: '{"release-candidate": "develop|hotfix/*"}'

# a repository where main takes releases too, not just hotfixes
breaking_change_additional_scope_rules: '{"main": "hotfix/*|release/*"}'
```

A base present in both takes the additional value — write the complete pattern
set for that base, not just the addition. Both objects must be JSON objects of
strings; anything else fails the job rather than silently gating nothing.

### Two label escape hatches

| Input | Default | Effect |
|---|---|---|
| `force_labels` | `breaking-change-review` | puts an out-of-scope pull request in scope |
| `skip_labels` | *(empty)* | takes an in-scope pull request out of it |

Both are matched case-insensitively and work from the pull request itself, with no
workflow edit. `skip_labels` is empty by default on purpose: an escape hatch
nobody declared is an escape hatch nobody reviewed.

### Ignored authors veto everything

`ignore_authors` (default `dependabot[bot]`) is checked before scope. A dependency
bump that happens to carry an upstream `BREAKING CHANGE:` note in its body is not a
breaking change in *this* repository, and there is no human on the other side to
ask.

Write the login however you know it. Bot logins have three spellings and all of
them match: REST returns `dependabot[bot]`, GraphQL returns `dependabot`, and
`gh pr view --json author` — what this job reads — returns `app/dependabot`. Both
affixes are stripped before comparing.

## Fails closed

Detection failing is not "no breaking changes" — it is "we do not know", and an
unknown blocks. A shallow clone, a missing base ref, a checkout error, an
unprotected Environment, or the detect job dying all produce a red check rather
than a green one.

When the caller hands detection over, it passes `unknown` if its own detection
did not complete, so the normalised `false` can never be mistaken for a clean
scan.

The only intentional way through without an approval is a `skip_labels` entry,
which is empty by default.

## Rejection closes the pull request

A rejection is a decision, and leaving the pull request open invites re-running
the gate until somebody approves. The pull request is closed, the reason is
posted as a comment, and **the branch is untouched** — reopening is one click.

Closing happens **only on a recorded rejection**, never on a cancellation.
Closing a pull request because a superseding push cancelled the run would be
indefensible, so the Environment's own approval log is the source of truth, not
the job conclusion.

Reading that log needs `actions: read`. A called workflow may only request
permissions its caller already holds, so this workflow does **not** declare it —
doing so would break every consumer whose entrypoint does not grant it. Instead
it reads the log through `MANAGE_TOKEN` when one is passed, and falls back to the
approval job's conclusion when it cannot: a rejection fails that job, while a
cancellation cancels the whole run and never reaches the verdict at all. The
fallback cannot name the reviewer, and says so in the comment.

Set `close_on_rejection: false` to fail the check without closing.

## The pull request's side of it

One comment, carrying `<!-- breaking-change-approval -->`, edited in place on
every run. It opens with the request and the link to the pending deployment, and
ends as the record of who decided what:

> ### 🚨 Breaking change — approval required
>
> A breaking-change commit was found on this branch, so merging it will force the
> next release to a **major** version.
>
> 👉 **[Review the pending deployment](#)** — *Review deployments* →
> `breaking-approval`.

The `breaking-change` label is applied while it waits and removed once resolved —
cosmetic, and a repository that never declared it still gets its gate.

## Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `pr_number` | number | `0` | Pull request to act on. `0` uses the one in the event payload. |
| `scope_rules` | string | `{"develop": "*", "main": "hotfix/*"}` | JSON object mapping an exact base branch to pipe-separated head globs. A base absent from it is never gated. Invalid JSON fails closed. |
| `additional_scope_rules` | string | *(empty)* | JSON object merged over `scope_rules`, key by key. A base in both takes this value. |
| `force_labels` | string | `breaking-change-review` | Comma-separated labels that put an out-of-scope pull request in scope. Case-insensitive. |
| `skip_labels` | string | *(empty)* | Comma-separated labels that take an in-scope pull request out of it. Empty keeps the gate closed. |
| `ignore_authors` | string | `dependabot[bot]` | Comma-separated logins never gated, checked before scope as a veto. Spelling is normalised. |
| `detected_breaking_changes` | string | *(empty)* | Detection computed by the caller — `true`, `false`, `unknown` when the caller's own detection did not complete, or empty to detect here. |
| `detected_acknowledged` | string | *(empty)* | Companion to the above — whether the author acknowledgement line is present. Context only. |
| `author_acknowledgement` | string | the `pr-validation` line | Shown to the reviewer as context. Never substitutes for the approval. |
| `close_on_rejection` | boolean | `true` | Close the pull request when a reviewer rejects. |
| `approval_reviewers` | string | *(empty)* | Who may answer the gate, as comma-separated `team:<slug>` or `user:<login>`. Empty takes the repository's CODEOWNERS. Used only to create the Environment when it does not exist. |
| `create_approval_environment` | boolean | `true` | Create `breaking-approval` when missing. Needs a token with repository administration rights. |
| `require_protected_environment` | boolean | `true` | Refuse to gate when `breaking-approval` exists without required reviewers. Leave on. |
| `label` | string | `breaking-change` | Applied while waiting, removed once resolved. Cosmetic. |
| `enable_comment` | boolean | `true` | Post and keep the comment updated. |
| `dry_run` | boolean | `false` | Report what would be gated without commenting, labelling, requesting an approval, or failing. |
| `runner_type` | string | `blacksmith-4vcpu-ubuntu-2404` | Runner label. Overridden by `vars.GENERAL_RUNNERS`. |

Whitespace around commas is tolerated.

## Outputs

| Output | Description |
|--------|-------------|
| `in_scope` | Whether the pull request was gated at all (`true`/`false`). |
| `has_breaking_changes` | Whether a breaking commit was found (`true`/`false`). Always `false` out of scope — nothing was scanned. |
| `approved` | Whether a reviewer approved through the Environment (`true`/`false`). |
| `result` | Gate verdict (`success`/`failure`). |

Through the umbrellas these surface as `breaking_change_approval_result`
(`success` / `failure` / `skipped`) and `breaking_change_approved_by_reviewer`.
`skipped` is reported rather than folded into `success`: a gate that never ran
and a gate that passed are not the same fact.

## Secrets

| Secret | Required | Description |
|--------|----------|-------------|
| `MANAGE_TOKEN` | No | Token with `pull-requests: write`; `actions: read` to name the reviewer and close on rejection; `administration: write` to create the Environment. Falls back to `github.token`, which can do none of the three. |

Fork pull requests get a read-only `github.token`, so the comment and the label
are skipped there while the verdict still decides the check. Pass `MANAGE_TOKEN`
in repositories that take contributions from forks.

## What detection actually matches

Delegated in full to the
[`breaking-change-guard`](../src/validate/breaking-change-guard/README.md)
composite, whose patterns are pinned to what the release parser accepts:

- a subject matching `^(\w*)(?:\((.*)\))?!: (.*)$` — the `!` form
- a message line matching `BREAKING CHANGE` / `BREAKING CHANGES` followed by a
  colon or whitespace, case-insensitive, optionally prefixed by whitespace, `*`
  or `|`

`BREAKING-CHANGE` and `-` bullets are **not** matched, because the configured
parser does not treat them as breaking either. Prose that merely mentions the
phrase mid-line is not matched.

Clearing a false positive therefore means rewording the commits — which is the
correct fix, since the commit message is what the release reads.

## Limitations

- **The run stays open while it waits.** That is the mechanism, not a bug: the
  pending deployment is what blocks the merge. Nothing in the validation graph
  depends on the gate, so a pull request waiting days for its approval still gets
  its title, source-branch, signature and report verdicts immediately.
- **Squash merges rewrite the message.** The gate reads the commits on the
  branch; what semantic-release later reads is whatever the merge produced. A
  repository that squashes should keep the pull request title under
  [`pr-title`](../src/validate/pr-title/README.md) validation.
- **The check is advice until it is required.** Making it a required status check
  is a repository setting, not something a workflow can declare.
- **Admins can merge anyway.** Intended — the gate makes the bump deliberate, not
  impossible.

## Local test

```bash
bash    src/validate/pr-gate-scope/test.sh
bash    src/validate/codeowners-reviewers/test.sh
bash    src/validate/breaking-change-guard/test.sh
python3 src/validate/breaking-change-guard/test-workflow.py
```

- **`pr-gate-scope/test.sh`** — 32 cases against a stubbed `gh`: the rules and
  their globs, the merge semantics of `additional-scope-rules`, both label
  overrides and their precedence, the three bot spellings, and every input that
  must fail closed. No network, no repository fixture.
- **`codeowners-reviewers/test.sh`** — 22 cases: both owner forms, comments,
  last-rule-wins, Enterprise section headers, the three file locations, the
  reviewer cap, and every shape that yields nothing.
- **`breaking-change-guard/test.sh`** — the detector itself, against real Git
  fixtures.
- **`test-workflow.py`** — the wiring: the literal `environment:`, that every
  orchestrated composite exists with its README and is pinned, that the preflight
  runs before the gate, that `outcome` does not declare a permission it cannot
  escalate to, and that a pull request is closed only on a recorded rejection.

<!-- smoke test: exercises the breaking-change approval gate. This PR is not meant to be merged. -->
