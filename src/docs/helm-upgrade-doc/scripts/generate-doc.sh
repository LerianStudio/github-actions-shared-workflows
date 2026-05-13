#!/usr/bin/env bash
set -euo pipefail

# Called by the helm-upgrade-doc composite action.
# All inputs come from environment variables set by the action.

NEW_MAJOR=$(echo "$NEW_VERSION" | cut -d. -f1)
NEW_MINOR=$(echo "$NEW_VERSION" | cut -d. -f2)
BASE_MAJOR=$(echo "$BASE_VERSION" | cut -d. -f1)

if [ "$BUMP_TYPE" = "patch" ]; then
  DOC_FILE="${DOCS_PATH}/UPGRADE-${NEW_VERSION}.md"
else
  DOC_FILE="${DOCS_PATH}/UPGRADE-${NEW_MAJOR}.${NEW_MINOR}.md"
fi

echo "📄 Target doc: $DOC_FILE"

if [ -f "$DOC_FILE" ]; then
  echo "✅ $DOC_FILE already exists — skipping generation"
  echo "doc_generated=false" >> "$GITHUB_OUTPUT"
  echo "doc_path="           >> "$GITHUB_OUTPUT"
  exit 0
fi

# Diff between previous tag and current tag
CHART_DIFF=$(git diff "${PREV_TAG}".."${CURRENT_TAG}" -- "${CHART_PATH}/Chart.yaml" 2>/dev/null || true)
VALUES_DIFF=$(git diff "${PREV_TAG}".."${CURRENT_TAG}" -- "${CHART_PATH}/values.yaml" 2>/dev/null | head -400 || true)
TEMPLATE_DIFF=$(git diff --name-status "${PREV_TAG}".."${CURRENT_TAG}" -- "${CHART_PATH}/templates/" 2>/dev/null || true)

# Load 2 most recent existing UPGRADE docs as few-shot examples
EXAMPLES=""
if [ -d "$DOCS_PATH" ]; then
  # shellcheck disable=SC2012
  while IFS= read -r doc_file; do
    DOC_NAME=$(basename "$doc_file")
    DOC_CONTENT=$(cat "$doc_file")
    EXAMPLES="$(printf '%s\n=== %s ===\n%s\n' "$EXAMPLES" "$DOC_NAME" "$DOC_CONTENT")"
  done < <(ls -t "${DOCS_PATH}"/UPGRADE-*.md 2>/dev/null | head -2)
fi

if [ "$BUMP_TYPE" = "major" ]; then
  TITLE_LINE="# Helm Upgrade from v${BASE_MAJOR}.x to v${NEW_MAJOR}.x"
  SECTION_HINT="Include: Topics ToC, Breaking Changes, Features or Additions, Migration Steps, Command to upgrade. Omit empty sections."
elif [ "$BUMP_TYPE" = "minor" ]; then
  TITLE_LINE="# Helm Upgrade from v${BASE_VERSION} to v${NEW_VERSION}"
  SECTION_HINT="Include: Topics ToC, Features or Additions, Command to upgrade. Add Breaking Changes only if the diff shows any. Omit empty sections."
else
  TITLE_LINE="# Helm Upgrade from v${BASE_VERSION} to v${NEW_VERSION}"
  SECTION_HINT="Include: Topics ToC, Fixes section, Command to upgrade. Keep it concise."
fi

UPGRADE_CMD="helm upgrade ${CHART_NAME} oci://registry-1.docker.io/lerianstudio/${CHART_NAME}-helm --version ${NEW_VERSION} -n ${CHART_NAME}"

# Build the full prompt via jq to handle special characters safely
PROMPT=$(jq -rn \
  --arg bv    "$BASE_VERSION" \
  --arg nv    "$NEW_VERSION" \
  --arg bt    "$BUMP_TYPE" \
  --arg cdiff "$CHART_DIFF" \
  --arg vdiff "$VALUES_DIFF" \
  --arg tdiff "$TEMPLATE_DIFF" \
  --arg ex    "$EXAMPLES" \
  --arg tl    "$TITLE_LINE" \
  --arg sh    "$SECTION_HINT" \
  --arg cmd   "$UPGRADE_CMD" \
  '"You are generating a Helm upgrade documentation file for the midaz-helm chart.\n\n" +
   "CONTEXT:\n- Chart: midaz-helm\n- Previous version: \($bv)\n- New version: \($nv)\n- Bump type: \($bt)\n\n" +
   "CHART.YAML DIFF:\n\($cdiff)\n\n" +
   "VALUES.YAML DIFF (first 400 lines):\n\($vdiff)\n\n" +
   "TEMPLATE FILE CHANGES:\n\($tdiff)\n\n" +
   "EXISTING UPGRADE DOCS (use as format and style reference):\n\($ex)\n\n" +
   "INSTRUCTIONS:\n" +
   "1. The first line must be exactly: \($tl)\n" +
   "2. \($sh)\n" +
   "3. Follow the exact format, writing style, and level of detail from the existing docs above.\n" +
   "4. The final section must always be:\n## Command to upgrade\n```bash\n\($cmd)\n```\n" +
   "5. Base content only on what the diffs show. Do not invent changes not present in the diff.\n" +
   "6. Output ONLY the markdown content. Do not wrap output in code fences."')

if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  echo "🤖 Using Anthropic API (claude-sonnet-4-6)"
  REQUEST_BODY=$(jq -n \
    --arg prompt "$PROMPT" \
    '{model: "claude-sonnet-4-6", max_tokens: 4000, messages: [{role: "user", content: $prompt}]}')

  HTTP_CODE=$(curl -s -w "%{http_code}" --max-time 90 --connect-timeout 10 \
    -o /tmp/upgrade_doc_response.json \
    https://api.anthropic.com/v1/messages \
    -H "content-type: application/json" \
    -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H "anthropic-version: 2023-06-01" \
    -d "$REQUEST_BODY")

  PROVIDER="Anthropic"
  CONTENT_EXPR='.content[0].text // empty'

elif [ -n "${OPENROUTER_API_KEY:-}" ]; then
  echo "🤖 Using OpenRouter ($OPENAI_MODEL)"
  REQUEST_BODY=$(jq -n \
    --arg model  "$OPENAI_MODEL" \
    --arg prompt "$PROMPT" \
    '{model: $model, messages: [{role: "user", content: $prompt}], temperature: 0.3, max_tokens: 4000}')

  HTTP_CODE=$(curl -s -w "%{http_code}" --max-time 90 --connect-timeout 10 \
    -o /tmp/upgrade_doc_response.json \
    https://openrouter.ai/api/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OPENROUTER_API_KEY" \
    -H "HTTP-Referer: https://github.com/${GITHUB_REPOSITORY}" \
    -H "X-Title: Helm Upgrade Doc" \
    -d "$REQUEST_BODY")

  PROVIDER="OpenRouter"
  CONTENT_EXPR='.choices[0].message.content // empty'

else
  echo "❌ Neither anthropic-api-key nor openrouter-api-key is set"
  exit 1
fi

if [ "$HTTP_CODE" -ge 400 ]; then
  echo "❌ ${PROVIDER} API returned HTTP $HTTP_CODE"
  cat /tmp/upgrade_doc_response.json 2>/dev/null || true
  rm -f /tmp/upgrade_doc_response.json
  exit 1
fi

CONTENT=$(jq -r "$CONTENT_EXPR" /tmp/upgrade_doc_response.json)
rm -f /tmp/upgrade_doc_response.json

if [ -z "$CONTENT" ]; then
  echo "❌ No content returned by the API"
  exit 1
fi

CONTENT=$(echo "$CONTENT" | sed '/^```/d')

mkdir -p "$DOCS_PATH"
printf '%s\n' "$CONTENT" > "$DOC_FILE"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📄 Generated: $DOC_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
head -30 "$DOC_FILE"
echo "..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "doc_generated=true" >> "$GITHUB_OUTPUT"
echo "doc_path=$DOC_FILE" >> "$GITHUB_OUTPUT"
