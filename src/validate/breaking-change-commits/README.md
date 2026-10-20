<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>Breaking Change Commits</h1></td>
  </tr>
</table>

> **Unreleased.** Until this ships in a release, reference it as `@develop` —
> `@v1` is the previous release and does not contain it yet.

Lists the commits in a pull request that carry a breaking change, and
fingerprints the set.

## Why a fingerprint

An approval is given to a specific breaking change, not to a pull request. Push
anything afterwards and the question becomes: *is this still the thing that was
approved?*

Without an answer, the only safe default is to ask again on every push — so a
reviewer who approved a breaking change gets asked the identical question
minutes later because the author fixed a typo. That is how a gate turns into a
formality people click through.

The fingerprint is built from the **SHAs** of the breaking commits, so:

| The author… | Fingerprint |
|---|---|
| fixes a typo in an unrelated file | unchanged |
| adds an ordinary commit | unchanged |
| rewords the breaking commit | changes — it is a different commit now |
| adds another breaking commit | changes |

Rewording counts as a change on purpose: the approval was given to the text that
was read, and the subject is what the release parser acts on.

## Which commits count

The same two forms the
[`breaking-change-guard`](../breaking-change-guard/README.md) detector accepts,
and no others:

- a subject with `!` after the type — `feat(scope)!: …`
- a message line that is a `BREAKING CHANGE` / `BREAKING CHANGES` footer,
  optionally prefixed by whitespace, `*` or `|`

`BREAKING-CHANGE` with a hyphen does not count, and neither does prose that
mentions the phrase mid-sentence — because the release parser treats neither as
breaking.

## Pull requests above 250 commits

`/pulls/{n}/commits` caps at 250. The action compares what the endpoint
returned against the `commits` count the pull request declares, and when the
two disagree it **exits non-zero** instead of reporting on a partial list — a
fingerprint built from the first 250 of 300 commits would miss a break living
in the tail and say "already approved" about a change nobody saw.

So a pull request over 250 commits fails the step rather than passing it. What
that costs depends on who is asking, and the two cases are not the same:

- **Detecting here** — nothing else looked, so the gate reads the failure as
  `unknown` and blocks. The way through is to split the pull request, not to
  widen the cap: the endpoint has no page beyond it.
- **Detection supplied by the caller** — `pr-validation` and the other
  umbrellas run the detector over the real commit range and pass the answer in.
  That answer stands, and the gate is not blocked by this step failing. What is
  lost is the fingerprint, so no earlier approval is reused and the reviewer is
  asked for a fresh decision. Nothing to split.

The same refusal fires if the declared count cannot be read at all.

## Commit subjects are untrusted text

The subjects go into `GITHUB_OUTPUT` as a multiline value, and whoever opens the
pull request writes them. With a fixed delimiter, a commit whose subject *is*
that delimiter closes the block early, and every line after it is read as a new
output assignment — `fingerprint=` included, which is what decides whether a
breaking change counts as already approved.

So the delimiter is random per run and checked against the subjects before
anything is written. The test suite includes the attack: two commits, one
closing the block and one assigning a forged fingerprint.

**This is a view, not a verdict.** The detector runs over the real commit range
and decides; this reads the API because the jobs that need it have no checkout.
They must agree, which is why the patterns are kept identical — and the tests
here cover the same negative cases.

## Resolving at a past revision

`at-sha` (with `base-ref`) resolves the set as it stood at that revision
instead of at the pull request's current head, by comparing `base-ref...at-sha`
rather than reading the pull request's commits — which always report the
current state.

The gate uses it for one question: *what did that approval approve?* The
fingerprint written in the approval record answers a different one — what the
writer claims it covered — and anybody who can read the repository can write a
record. Since the fingerprint is derived from public commit SHAs it is also
computable in advance, so a record naming a real approved run could be posted
before the breaking commit it claims to cover even exists. Resolving from the
approving run's own head closes that: the head is not writable.

The 250 cap applies here too, measured against `total_commits`, and is refused
the same way.

**This path needs `contents: read`.** The comparison API is repository
contents, not pull request data, so a token carrying only `pull-requests: read`
fails every comparison — and a failed comparison reads as "cannot confirm what
that approval covered", which means the approval is not reused and the reviewer
is asked again on every push. Nothing says why, so grant the scope.
`breaking-change-approval.yml` already does for its own `request` job; this
applies to anything calling the composite directly.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `github-token` | Token used to read the commits. Needs `pull-requests: read` — and `contents: read` as well when `at-sha` is given. | Yes | — |
| `pr-number` | Pull request whose commits are listed. | Yes | — |
| `repository` | Repository owning it, as `owner/name`. | No | `${{ github.repository }}` |
| `at-sha` | Resolve the set as it stood at this revision instead of at the current head. Requires `base-ref`. | No | `''` |
| `base-ref` | Base of the comparison when `at-sha` is given. | No | `''` |

## Outputs

| Output | Description |
|--------|-------------|
| `count` | How many commits carry a breaking change. |
| `shas` | Comma-separated SHAs, in commit order. |
| `subjects` | Their subjects, one per line. |
| `fingerprint` | Short digest of the SHA set. Empty when there is none. |

## Usage

Testing, while this is unreleased — `@develop` is the only ref that resolves
today. After it ships, pin a tier channel (`@tier-0` / `@tier-1` / `@tier-2`)
and never `@develop`, which moves under the caller.

```yaml
- name: List the breaking-change commits
  id: breaking
  uses: LerianStudio/github-actions-shared-workflows/src/validate/breaking-change-commits@develop
  with:
    github-token: ${{ secrets.MANAGE_TOKEN || github.token }}
    pr-number: ${{ github.event.pull_request.number }}

- name: Ask only if this is not what was already approved
  if: steps.breaking.outputs.fingerprint != steps.previous.outputs.approved_fingerprint
  run: echo "needs a decision"
```

## Local test

```bash
bash src/validate/breaking-change-commits/test.sh
```

20 cases against a stubbed `gh`: both breaking forms, the two lookalikes that
must not count, ordering, the fingerprint staying put when an ordinary commit is
added while changing when a breaking one is, parity with the detector on case
and on scopes containing parens, and the output-injection attack.
