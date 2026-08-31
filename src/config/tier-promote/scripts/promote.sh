#!/usr/bin/env bash
# Promotes one already-resolved commit into one tier branch.
#
# The promotion is a COMMIT, never a ref move and never a merge:
#
#   * Not a ref move, because the tier branches are expected to diverge in
#     content from `main` once the self-reference rewrite lands, and because
#     the `tier-rule` ruleset blocks `non_fast_forward` — a commit on top of
#     the tier tip is always a fast-forward, a moved ref may not be.
#   * Not a merge, because `main` and the tier branch will differ on the very
#     lines the rewrite touches, so every promotion would conflict. Instead the
#     promoted tree is materialized wholesale onto the tier tip with
#     `git read-tree`, producing exactly one commit whose tree IS the promoted
#     tree. No conflict is possible, by construction.
#
# Idempotent: promoting a commit whose tree already matches the tier tip is a
# no-op. Promoting an OLDER tag is how a rollback is performed — it lands as a
# new forward commit carrying the older tree, so no force push is ever needed.
#
# Required env:
#   REPO           owner/name
#   TIER           tier branch to promote into (e.g. tier-0)
#   TAG            stable tag being promoted (e.g. v1.63.0)
#   SOURCE_SHA     commit the tag resolves to, pinned by the caller for the
#                  whole train so every tier promotes the same tree
#   GH_TOKEN       token with contents:write and pull-requests:write on REPO
# Optional env:
#   DRY_RUN        true to report the intended change without writing
#   AUTO_MERGE     true to enable auto-merge on a fallback PR
set -euo pipefail

# The caller captures this script's stdout as JSON, so every chatty subprocess
# (git commit's summary line, push progress, gh pr create's URL echo) must not
# leak into it. stdout goes to stderr for the whole script; the final jq writes
# the result through FD 3.
exec 3>&1 1>&2

: "${REPO:?}" "${TIER:?}" "${TAG:?}" "${SOURCE_SHA:?}" "${GH_TOKEN:?}"
dry_run="${DRY_RUN:-false}"
auto_merge="${AUTO_MERGE:-false}"

export GITHUB_TOKEN="$GH_TOKEN"

emit() {
  jq -n \
    --arg tier "$TIER" --arg tag "$TAG" --arg action "$1" \
    --arg url "${2:-}" --arg commit "${3:-}" \
    '{tier:$tier, tag:$tag, action:$action, url:$url, commit:$commit}' >&3
}

# Work in a throwaway clone rather than the job workspace. The workspace holds
# this very script (the composite is loaded from `./src/...`), and replacing the
# working tree underneath a running script is asking for trouble.
work=$(mktemp -d)
push_err=$(mktemp)
cleanup() { rm -rf -- "$work"; rm -f -- "$push_err"; }
trap cleanup EXIT

git clone --quiet --branch "$TIER" \
  "https://x-access-token:${GH_TOKEN}@github.com/${REPO}.git" "$work"
cd "$work"

git fetch --quiet origin "refs/tags/${TAG}:refs/tags/${TAG}"

# Guard against a tag moved between the caller resolving it and this job
# running: the tree we promote must be the one the train was opened on.
tag_sha=$(git rev-list -n1 "refs/tags/${TAG}")
if [[ "$tag_sha" != "$SOURCE_SHA" ]]; then
  echo "::error::tag ${TAG} now points at ${tag_sha}, but this train was pinned to ${SOURCE_SHA} — refusing to promote"
  exit 1
fi

# Materialize the promoted tree on top of the tier tip. HEAD stays on the tier
# branch; only the index and working tree are replaced.
git read-tree --reset -u "$SOURCE_SHA"

if git diff --cached --quiet HEAD; then
  echo "::notice::${TIER} already carries the tree of ${TAG} — nothing to promote"
  emit "skip" "" "$(git rev-parse HEAD)"
  exit 0
fi

echo "Changes ${TIER} would receive from ${TAG}:"
git diff --cached --stat HEAD

if [[ "$dry_run" == "true" ]]; then
  echo "::notice::dry run — ${TIER} not modified"
  emit "dry-run" "" ""
  exit 0
fi

subject="chore(promote): ${TIER} to ${TAG}"
body="Promotes the tree of ${TAG} (${SOURCE_SHA}) into ${TIER}.

Consumers pinned to @${TIER} receive this on their next workflow run."

# Committer identity and GPG signing are configured globally by the caller
# workflow (crazy-max/ghaction-import-gpg with git_config_global). Do NOT set
# them here — that would replace the signing identity, and the `tier-rule`
# ruleset requires signed commits on refs/heads/tier-*.
#
# `[skip ci]` on the direct-push path: nothing in this repo triggers on a push
# to tier-*, and the promotion carries no change that needs re-validation here.
git commit --quiet -m "$subject" -m "$body" -m "[skip ci]"

action="unknown"
url=""

if git push --quiet origin "HEAD:refs/heads/${TIER}" 2>"$push_err"; then
  action="push"
else
  echo "::warning::direct push to ${TIER} failed, falling back to PR"
  cat "$push_err" >&2

  # `[skip ci]` is wrong for a PR: the base branch may gate merging on required
  # status checks, and skipped CI leaves such a PR permanently unmergeable. The
  # rejected push never landed anywhere, so amending is safe.
  git commit --quiet --amend -m "$subject" -m "$body"

  pr_branch="promote/${TIER}/${TAG}"
  git push --quiet -f origin "HEAD:refs/heads/${pr_branch}"

  pr_body="${body}

Direct push to \`${TIER}\` was rejected, so this promotion is going through a PR. Generated by [tier-promote](https://github.com/${REPO}/blob/main/config/tier-promotion.yml)."

  # Re-running a promotion that already fell back once would force-push this
  # branch (done above) and then hit `gh pr create` failing on the existing
  # base/head pair. Under `set -e` that exits before any JSON is emitted,
  # leaving the caller with a failed step and a branch already updated. Look
  # for the open PR first and reuse it.
  url=$(gh pr list \
    --repo "$REPO" \
    --base "$TIER" \
    --head "$pr_branch" \
    --state open \
    --limit 1 \
    --json url --jq '.[0].url // ""')

  if [[ -n "$url" ]]; then
    echo "::notice::reusing open promotion PR ${url} (branch was force-updated to the current attempt)"
  else
    url=$(gh pr create \
      --repo "$REPO" \
      --base "$TIER" \
      --head "$pr_branch" \
      --title "$subject" \
      --body "$pr_body")
  fi
  action="pr"

  if [[ "$auto_merge" == "true" ]]; then
    gh pr merge --auto --squash "$url" \
      || echo "::warning::could not enable auto-merge on ${url}, it will stay open"
  fi
fi

emit "$action" "$url" "$(git rev-parse HEAD)"
