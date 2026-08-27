# CodeRabbit gate — throwaway test file

This file exists only to verify that the CodeRabbit review gate holds when a
required check fails. **Do not merge this PR.** Close it and delete the branch
once the behaviour has been observed.

## What is being tested

`gate-coderabbit` in `.github/workflows/self-pr-validation.yml` applies the
`review-ready` label only when no required check failed. With
`reviews.auto_review.enabled: false` in `.coderabbit.yml`, that label is the
trigger for a review — so no label means no review.

The two words below are misspelled on purpose, which makes `Spelling Check`
fail. It runs whenever any file changes, so it is the most reliable check to
break deliberately:

- enviroment
- recieve

## Expected outcome

| Step | Expectation |
|------|-------------|
| `Spelling Check` | fails on the two words above |
| `gate-coderabbit` | skipped — its `if:` requires no failure among `needs` |
| `review-ready` | never applied |
| CodeRabbit | posts no review |

A summary/walkthrough comment may still appear: `high_level_summary` is
independent of `auto_review.enabled` and is not governed by the gate.
