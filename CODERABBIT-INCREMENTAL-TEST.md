# CodeRabbit gate — throwaway measurement

**Do not merge.** Close and delete the branch once measured.

## Question

Under the current config (`auto_review.enabled: false`, no `labels`), does
CodeRabbit keep reviewing later pushes **on its own** — incremental review — or
does every revision need its own `@coderabbitai review` from the gate?

This decides whether the gate should comment once per pull request or once per
push, which in turn decides how noisy the pull request gets.

## Method

1. First push: the gate comments, CodeRabbit reviews. Confirms engagement.
2. Second push: the gate is **suppressed** by pre-posting only its idempotency
   marker — the HTML comment without the command — so it finds the marker and
   stays quiet.
3. Watch for a review with no command in between.

A review appearing at step 3 means incremental works and the command is only
needed once. No review means every revision needs its own command.

## Prior evidence, and why it is not enough

On #705, two reviews landed at 14:15:23 and 14:22:11 after the trigger label had
been removed at 14:09:59 — suggesting incremental runs unprompted. But that was
under the label-based regime, and the decision may have been taken before the
label was removed. Nothing has been measured under the command-based config.

## Section for the second revision

<!-- second push appends below this line -->
