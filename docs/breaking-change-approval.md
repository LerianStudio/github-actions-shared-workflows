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
| [`breaking-change-guard`](../src/validate/breaking-change-guard/README.md) | The canonical detector, over the real commit range. Runs in `pr-validation.yml`, whose verdict this gate is handed |
| [`breaking-change-commits`](../src/validate/breaking-change-commits/README.md) | Which commits carry the break, and a digest of the set |
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

## Who answers the gate

Three sources, in order. The first that yields anybody wins:

1. **`approval_reviewers`** — the caller named them explicitly.
2. **CODEOWNERS**, read from the pull request's **base** ref. Reading the head
   would let an author edit who is allowed to approve their own change.
3. **`fallback_reviewers`** — through `pr-validation`, the
   `BREAKING_APPROVAL_FALLBACK_REVIEWERS` organisation variable.

The third exists because of what the second actually finds.
`codeowners-reviewers` reads the **catch-all `*` rule**, which is the right
question for a repository-wide gate — but most CODEOWNERS files do not have
one. Measured across the consuming repositories before this was added: four of
five carried rules only for specific paths (`/.github/`, `/.releaserc.yml`),
and no `*`.

In those four the gate resolved no reviewer at all. An Environment cannot be
created without one — `environment-protection` refuses, because an Environment
created without required reviewers is a gate that approves itself — so the
preflight failed, and the first breaking change in each of those repositories
would have been blocked by a gate nobody could answer.

Set the organisation variable once and that stops being a per-repository
problem:

```
BREAKING_APPROVAL_FALLBACK_REVIEWERS = team:your-devops-team
```

Leaving it unset keeps the old behaviour: no reviewer, no Environment, and a
refusal rather than an invented approver. That is deliberate — a gate that
quietly picks someone to ask is worse than one that says it cannot run.

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

Called this way the workflow detects on its own, through the API — it checks
out nothing at all.

It used to use two checkouts and read Git directly. CodeQL flagged that as
`actions/untrusted-checkout`, and the alert was fair: a non-privileged workflow
was placing a contributor's tree on disk next to `MANAGE_TOKEN`. Nothing ever
executed it, but nothing needed it either, and the tree, the token exposure and
the alert all went away together.

The acknowledgement is **not** evaluated on this path — the detector that reads
the pull request description runs in `pr-validation.yml`. The comment omits that
row rather than reporting it missing, because telling an author to add a line no
check is asking for is worse than saying nothing.

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

## An approval survives a push that did not change the breaking change

The gate asks about a specific breaking change, not about a pull request. So it
remembers which one was approved, and only asks again when that changes.

| The author… | Asked again? |
|---|---|
| fixes a typo the review pointed out | no |
| adds an ordinary commit | no |
| rewords the breaking commit | **yes** — it is different text now |
| adds another breaking commit | **yes** |

This matters more than convenience, because of how the review gate is wired:
CodeRabbit only runs once every check has passed, which includes this one. So
without the memory, every iteration of *approve → review → fix → push* would
need a fresh human approval to get the next review — and the reviewer would be
answering the identical question each time. A question asked five times gets a
reflex answer by the third.

**How it is remembered.** `breaking-change-commits` digests the SHAs of the
breaking commits. When an approval lands, the comment records that digest
together with the run that carried the approval:

```html
<!-- breaking-change-approved: 4f2a9c1e8b3d7a60 run=38905110563 -->
```

Every later run rebuilds the digest and looks for its record. A match skips the
Environment gate entirely; anything else asks again. Records accumulate, so
returning to a previously approved set is still approved.

Built from SHAs, so a reword counts as a change — the approval was given to the
text that was read, and the subject is what the release parser acts on.

### The record is checked, not believed

A comment is not evidence. Anyone who can read the repository can comment on a
pull request, and the fingerprint is computable from public data: the commit
SHAs are on the pull request and the digest is defined in this repository. A
record on its own is therefore something a stranger can write.

So three things must hold before an approval is reused:

1. the record sits in a comment from an **owner or member** of the
   organisation, or from `github-actions[bot]` — the identity the reporter
   writes under when no `MANAGE_TOKEN` is passed, and one nobody but Actions
   can author as
2. the **run it names really was approved** for the `breaking-approval`
   Environment, read from the Environment's own approval log, and that run is
   on this head branch
3. the **set that run approved** is this set — resolved from the run's own
   `head_sha`, never from the fingerprint written in the record

Every record for the fingerprint is tried, not only the first: runs are deleted
on the repository's retention schedule, so the oldest record goes unverifiable
while a newer one is still good.

The third was missing until @fredcamaral demonstrated what it cost. The first
two establish that *an* approval happened on this branch; neither says what it
approved. Since the fingerprint is derived from public commit SHAs it is
computable before the commit exists, so a member could post a record carrying
`fp(A,B)` pointing at the run that approved only `A`, then push the breaking
commit `B` — and the gate would read "already approved" and return success with
no reviewer involved. Resolving the approved set from the run's own head closes
it: the record now says only *which run to ask*, and the run answers.

When that resolution fails — a deleted run, an unreadable comparison, a pull
request past the commit cap — the approval is not reused. Not knowing is not
evidence that it still applies.

Only a run whose Environment approval actually happened writes a record. A
reused approval reports `approved` with the gate job skipped, and a record
naming *that* run would assert something no log can confirm — then outlive the
real one.

The second is what carries the weight. Writing the text is easy; producing a run
whose Environment approval actually happened is not.

Verifying needs `actions: read`. Where that is unavailable the check cannot be
made, so the approval is **not** reused and the reviewer is asked again — asking
twice costs attention, trusting an unverified record costs the gate.

**The records are never rewritten blind.** If the comment cannot be read back,
the reporter fails rather than replacing it, because a rewrite without the
records would erase approvals already given and send reviewers questions they
had already answered.

## One open request, and approvals expire on a push

Every push queues another pending deployment, and GitHub does not retire the
previous one. Left alone, a reviewer's queue fills with requests tied to commits
that are no longer the head — and approving one of those approves a revision
nobody is merging, while the live one still waits.

The approval job is therefore under a `concurrency` group keyed to the pull
request, with `cancel-in-progress`. A push cancels the pending request and
replaces it with one for the new head.

That is what retires a *pending* request. An approval that already landed is a
different matter — see above: it is remembered against the change it approved,
and only a change to that change asks again.

**A cancelled run never touches the pull request.** The verdict job still runs
when its approval is cancelled, and without a guard it would overwrite the live
revision's comment with *"the approval did not complete"* — true of the dead run,
misleading about the live one.

Two signals, and the order matters. A **cancelled approval** is the broad one:
nothing cancels it except the concurrency group replacing the run or a human
doing it by hand, and neither is a decision to report. A **changed head** is the
narrower one, for anything that slipped past the first.

The cancelled check cannot be dropped in favour of the head comparison, because
a run can be replaced without the head moving at all: editing the description
fires `edited`, which queues a new run on the very same commit.

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

Two labels, and they expire at different times. `breaking-change` states a fact
about the commits and **survives the approval** — the break does not stop being a
break because somebody agreed to it, and a search for that label months later
should still find this pull request. It comes off only when the breaking commits
are gone. `awaiting-breaking-approval` states that a decision is pending, and
comes off the moment one is made.

Both are cosmetic: a repository that never declared them still gets its gate.
Declare them with [`labels-sync`](labels-sync.md), or pass `label: ''` /
`pending_label: ''` to turn them off.

> **Behaviour change.** `label` used to be removed once the change was approved
> or rejected. If you set it as a temporary waiting marker, move that value to
> `pending_label` and set `label: ''` — otherwise the marker now stays on the
> pull request after the decision.
>
> Callers on the default need nothing: `breaking-change` staying put is the
> point, and `awaiting-breaking-approval` takes over the transient role.

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
| `fallback_reviewers` | string | *(empty)* | Who answers when `approval_reviewers` is empty **and** CODEOWNERS yields nobody. Through `pr-validation` this defaults to the `BREAKING_APPROVAL_FALLBACK_REVIEWERS` organisation variable. Empty refuses rather than inventing a reviewer. |
| `create_approval_environment` | boolean | `true` | Create `breaking-approval` when missing. Needs a token with repository administration rights. |
| `require_protected_environment` | boolean | `true` | Refuse to gate when `breaking-approval` exists without required reviewers. Leave on. |
| `label` | string | `breaking-change` | States that the change is breaking. A fact, so it survives the decision and comes off only when the breaking commits are gone. Cosmetic. |
| `pending_label` | string | `awaiting-breaking-approval` | States that a decision is pending. A state, so it comes off once approved or rejected. Cosmetic. |
| `enable_approval` | boolean | `true` | Hold breaking changes at the Environment. `false` keeps the gate reporting and labelling but never asks for a decision — the author acknowledgement is a separate control the caller still enforces, and the comment carrying the line to paste comes from here. Not the same as not calling the workflow. |
| `status_context` | string | *(empty)* | Publish the verdict as a commit status under this name — the one check name that is identical in every repository. Through `pr-validation` this defaults to the `BREAKING_APPROVAL_STATUS_CONTEXT` organisation variable. Needs `statuses: write`. Empty publishes nothing. |
| `enable_comment` | boolean | `true` | Post and keep the comment updated. |
| `dry_run` | boolean | `false` | Report what would be gated without commenting, labelling, requesting an approval, or failing. |
| `runner_type` | string | `blacksmith-4vcpu-ubuntu-2404` | Runner label. Overridden by `vars.GENERAL_RUNNERS`. |

Whitespace around commas is tolerated.

## Outputs

| Output | Description |
|--------|-------------|
| `in_scope` | Whether the pull request was gated at all (`true`/`false`). |
| `has_breaking_changes` | Whether a breaking commit was found (`true`/`false`). Reports the detection out of scope too — not gating a pull request is not the same as it carrying no break. Gate on `in_scope` alongside it for the earlier reading. |
| `approved` | Whether a reviewer approved through the Environment (`true`/`false`). |
| `result` | Gate verdict (`success`/`failure`). |

Through the umbrellas these surface as `breaking_change_approval_result`
(`success` / `failure` / `skipped`) and `breaking_change_approved_by_reviewer`.
`skipped` is reported rather than folded into `success`: a gate that never ran
and a gate that passed are not the same fact.

## Behaviour changes since v1.84

Two behaviours changed after the gate's first release in `v1.84.0`. Both were
deliberate, and neither is classified as breaking — for different reasons,
which are worth keeping apart:

- **The `label` input.** None of the umbrellas — `pr-validation`,
  `go-pr-validation`, `js-pr-validation` — expose an input for it; they pass
  `force_labels` and `skip_labels` and nothing else. A caller on that path
  never had a custom label to lose. Only a standalone caller that set one
  inside the release window can notice.
- **The `has_breaking_changes` output.** This one is about reading, not
  configuring, so the argument above does not reach it. What does: the
  umbrellas do not surface *this* output. Their `has_breaking_changes` comes
  from the `breaking-change-guard` job, which is unchanged; the only gate
  outputs they publish are `breaking_change_approval_result` and
  `breaking_change_approved_by_reviewer`. So again only a standalone caller
  can see it — one that branches on the output, whether or not it sets a
  label.

Written down anyway — an unannounced behaviour change is worse than a
documented one, whatever the version number says.

**`label` survives the decision.** It used to come off on approval. It is a
fact about the change — approving a break does not make it stop being one, and
somebody filtering for `breaking-change` three months from now wants this pull
request in the results. It is removed only when the breaking commits are gone.

The waiting marker moved to its own input:

```yaml
# before — one label doing both jobs
with:
  label: waiting-for-review

# after — the fact and the state, separately
with:
  label: ''                          # or breaking-change, the default
  pending_label: waiting-for-review  # comes off on approval or rejection
```

A caller that left `label` at its default needs no change.

**`has_breaking_changes` reports detection out of scope.** It used to be forced
to `false` whenever the gate did not apply, which conflated "not gated here"
with "carries no break". It now passes through what the caller detected. To get
the old reading, gate on `in_scope`:

```yaml
if: >-
  needs.gate.outputs.in_scope == 'true'
  && needs.gate.outputs.has_breaking_changes == 'true'
```

Nothing supplied is still `false` — the gate does not scan out of scope, so
there is no answer to report.

## Requiring the gate in a branch rule

The gate's job surfaces as a check named after the **caller's** job path —
`validate / PR Metadata / Breaking Change Approval / Breaking Change Approval`
in one repository, `validation / Breaking Change Approval / Breaking Change
Approval` in another. The prefix comes from the consumer's own workflow file,
so the same gate appears under several different names across an organisation.
Measured across the repositories consuming the umbrellas: **six distinct
names**. Required status checks match the context exactly, with no wildcard, so
no single organisation ruleset can require it — and a required check that never
arrives leaves every pull request pending forever.

`status_context` removes the caller from the name. The gate publishes a commit
status, which carries no job path, so the same string works everywhere — the
reason `CodeRabbit` and `Socket Security` look identical in every repository.

```
BREAKING_APPROVAL_STATUS_CONTEXT = breaking-change-approval
```

Then one organisation ruleset requires `breaking-change-approval` and covers
every repository, whatever its jobs are called.

Four things worth knowing:

- **It goes `pending` before the gate waits**, and only then. GitHub reads the
  latest status for a context, so without it the previous run's `success` stays
  current while this run sits at the Environment — and the rule would allow a
  merge on a decision nobody has given. The head SHA does not have to change
  for that: `edited` re-runs on the same commit, and retargeting a pull request
  moves it in or out of the gate's scope.
- **It is published on every run that reaches a verdict**, including those with
  nothing to approve. Out of scope and no breaking commits both publish
  `success`. A status that only appears sometimes cannot be required.
- **A superseded run publishes nothing.** Its verdict describes a revision that
  is no longer current and carries `result: failure`, so publishing it would
  overwrite the live run's success and block the pull request on a decision
  already given. The same rule the comment and the close already follow.
- **`result` decides pass or fail**, not the state. The state only chooses the
  wording, and the two are not allowed to disagree.
- **It needs `MANAGE_TOKEN` carrying `statuses: write`.** The job declares its
  own `permissions:`, which replaces whatever the caller granted — so granting
  `statuses: write` upstream has no effect here. Declaring it on the job is not
  an option either: a called workflow may only ask for permissions the caller
  already holds, so it would break every consumer that does not hold it. Hence
  the token. Without one that can write, the step warns and carries on rather
  than failing — but a rule requiring the status will stay pending, so check
  the warning before turning the rule on.

Requiring the job name instead still works for a single repository, and this
repository does exactly that. Prefer the status wherever one rule has to cover
more than one repository.

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

All five run in self CI under **Breaking Change Guard Detector Tests**. Three
of them did not until recently — 76 cases, including the output-forgery and
fingerprint ones, that a change could walk past without anything going red.

```bash
bash    src/validate/pr-gate-scope/test.sh
bash    src/validate/breaking-change-commits/test.sh
bash    src/validate/codeowners-reviewers/test.sh
bash    src/validate/breaking-change-guard/test.sh
python3 src/validate/breaking-change-guard/test-workflow.py
```

- **`pr-gate-scope/test.sh`** — 32 cases against a stubbed `gh`: the rules and
  their globs, the merge semantics of `additional-scope-rules`, both label
  overrides and their precedence, the three bot spellings, and every input that
  must fail closed. No network, no repository fixture.
- **`breaking-change-commits/test.sh`** — 22 cases: both breaking forms, the
  lookalikes that must not count, parity with the detector on case and on scopes
  containing parens, the fingerprint holding still for an ordinary commit while
  changing for a breaking one, and the output-injection attack a commit subject
  can otherwise mount.
- **`codeowners-reviewers/test.sh`** — 22 cases: both owner forms, comments,
  last-rule-wins, Enterprise section headers, the three file locations, the
  reviewer cap, and every shape that yields nothing.
- **`breaking-change-guard/test.sh`** — the detector itself, against real Git
  fixtures.
- **`test-workflow.py`** — the wiring: the literal `environment:`, that every
  orchestrated composite exists with its README and is pinned, that the preflight
  runs before the gate, that `outcome` does not declare a permission it cannot
  escalate to, and that a pull request is closed only on a recorded rejection.
