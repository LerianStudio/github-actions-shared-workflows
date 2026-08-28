# CodeRabbit gate — throwaway test file

**Do not merge.** Close this pull request and delete the branch once the
behaviour has been observed.

## What is being tested

PR #713 restored `reviews.auto_review.base_branches` in `.coderabbit.yml`, which
#708 had removed on the wrong premise that it was made redundant by
`enabled: false`. It is not: `base_branches` and `labels` are two independent
filters and both must pass.

With the key absent, the eligible set fell back to the default branch alone, and
every pull request into `develop` was refused with:

> Auto reviews are disabled on base/target branches other than the default branch.

This pull request exists because the fix **cannot validate itself**. CodeRabbit
reads `.coderabbit.yml` from the base branch, not from the head, so #713 was
still judged by the broken config it was fixing. Only a pull request opened
*after* the merge is judged by the corrected one.

It also cannot be validated on #712: that pull request already carries
`review-ready`, applied at 00:17 while the config still refused its base. Adding
a label that is already present is a no-op, so no event exists for CodeRabbit to
react to.

## Expected outcome

| Step | Expectation |
|------|-------------|
| Every required check | passes |
| `Release CodeRabbit Review` | applies `review-ready` |
| CodeRabbit | reviews this pull request |

The review is the whole point: it is what proves the base is eligible again.

If CodeRabbit still reports *"Auto reviews are disabled on base/target branches
other than the default branch"*, the fix is wrong and the finding is worth more
than this pull request.
