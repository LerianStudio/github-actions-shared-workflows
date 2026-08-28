# CodeRabbit gate — throwaway test file

**Do not merge.** Close this pull request and delete the branch once the
behaviour has been observed.

## What is being tested

Whether `@coderabbitai review`, posted by CI, is what triggers the review — with
no label able to take the credit.

#715 changed the gate from applying a `review-ready` label to posting the
command, and removed `labels` from `.coderabbit.yml` so the label can no longer
act as a trigger. Every earlier attempt to verify this was ambiguous:

| Pull request | Why it could not settle the question |
|---|---|
| #715 | both triggers were live at once, 2 seconds apart, because the config in force still came from `develop` |
| #714 | its branch predates the change and carries the old label-based gate |
| #712 | already carried the label from before the fix, so no event existed to react to |

This branch is the first cut from a `develop` that has the command gate **and**
no label trigger, so nothing else can explain a review appearing.

## Expected outcome

| Step | Expectation |
|------|-------------|
| Every required check | passes |
| `Request CodeRabbit Review` | posts `@coderabbitai review` with a commit marker |
| `review-ready` | applied as a cosmetic marker, after the comment |
| CodeRabbit | reviews this pull request |

**A review appearing proves the command works**, since no label trigger exists
any more. It also settles the second question: the label is applied two seconds
after the comment and is not consulted by anything, so it is decoration.

If no review appears, the note CodeRabbit posted on #715 was literal —
*"This command is applicable only when automatic reviews are paused"* — the
premise behind #715 is wrong, and the rollback is one line: restore
`labels: ["review-ready"]` in `.coderabbit.yml`.

Note that reviews are currently rate-limited to one per hour for this
organisation, so absence of a review is only meaningful after that window.
