# CodeRabbit gate — throwaway test file

This file exists only to verify that the CodeRabbit review gate holds when a
required check fails. **Do not merge this PR.** Close it and delete the branch
once the behaviour has been observed.

## What is being tested

`gate-coderabbit` in `.github/workflows/self-pr-validation.yml` applies the
`review-ready` label only when no required check failed. With
`reviews.auto_review.enabled: false` in `.coderabbit.yml`, that label is the
trigger for a review — so no label means no review.

## First revision — red path (confirmed)

The first commit carried two deliberate misspellings, which failed
`Spelling Check`. That check runs whenever any file changes, so it is the most
reliable one to break on purpose. Observed on commit `b263f5d`:

| Step | Expected | Observed |
|------|----------|----------|
| `Spelling Check` | fails | failed on both words |
| `gate-coderabbit` | skipped | skipped |
| `review-ready` | never applied | never applied |
| CodeRabbit | no review | no review, no inline comments |

CodeRabbit stated the reason itself, rather than staying silent:

> Review skipped — auto reviews are limited based on label configuration.
> Required labels (at least one): `review-ready`.
> Excluded labels (none allowed): `skip-coderabbit`.

A summary/walkthrough comment did appear: `high_level_summary` is independent of
`auto_review.enabled` and is not governed by the gate.

## Second revision — transition to green

This revision fixes both spellings, so every required check should pass. It
exercises the one path the earlier PRs never covered: a revision going from red
to green on the same pull request.

| Step | Expectation |
|------|-------------|
| `Hold CodeRabbit Review` | runs (this push is a `synchronize`) and finds nothing to withdraw |
| `Spelling Check` | passes |
| `gate-coderabbit` | runs and applies `review-ready` |
| CodeRabbit | reviews, now that the revision earned the label |
