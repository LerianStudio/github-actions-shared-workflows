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

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `github-token` | Token used to read the commits. Needs `pull-requests: read`. | Yes | — |
| `pr-number` | Pull request whose commits are listed. | Yes | — |
| `repository` | Repository owning it, as `owner/name`. | No | `${{ github.repository }}` |

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
