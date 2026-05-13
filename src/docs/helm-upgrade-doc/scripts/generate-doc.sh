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
  SECTION_HINT="Include: Topics ToC, Breaking Changes, Features or Additions, Migration Steps, Preview changes before upgrading, Command to upgrade. Omit empty sections."
elif [ "$BUMP_TYPE" = "minor" ]; then
  TITLE_LINE="# Helm Upgrade from v${BASE_VERSION} to v${NEW_VERSION}"
  SECTION_HINT="Include: Topics ToC, Features or Additions, Preview changes before upgrading, Command to upgrade. Add Breaking Changes only if the diff shows any. Omit empty sections."
else
  TITLE_LINE="# Helm Upgrade from v${BASE_VERSION} to v${NEW_VERSION}"
  SECTION_HINT="Include: Topics ToC, Fixes section, Preview changes before upgrading, Command to upgrade. Keep it concise."
fi

if [ "$CHART_NAME" = "plugin-access-manager" ] || [ "$CHART_NAME" = "otel-collector-lerian" ]; then
  PACKAGE_NAME="$CHART_NAME"
else
  PACKAGE_NAME="${CHART_NAME}-helm"
fi
UPGRADE_CMD="helm upgrade ${CHART_NAME} oci://registry-1.docker.io/lerianstudio/${PACKAGE_NAME} --version ${NEW_VERSION} -n ${CHART_NAME}"
DIFF_CMD="helm diff upgrade ${CHART_NAME} oci://registry-1.docker.io/lerianstudio/${PACKAGE_NAME} --version ${NEW_VERSION} -n ${CHART_NAME}"

# Build the full prompt via jq to handle special characters safely
PROMPT=$(jq -rn \
  --arg cn    "$CHART_NAME" \
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
  --arg diff  "$DIFF_CMD" \
  '"You are writing a Helm upgrade GUIDE for operators who need to upgrade the \($cn) chart from v\($bv) to v\($nv).\n" +
   "This is NOT a changelog. It is a practical operator guide that explains WHAT changed, WHY it matters, and HOW to handle it.\n\n" +
   "CONTEXT:\n- Chart: \($cn)\n- Previous version: \($bv)\n- New version: \($nv)\n- Bump type: \($bt)\n\n" +
   "CHART.YAML DIFF:\n\($cdiff)\n\n" +
   "VALUES.YAML DIFF (first 400 lines):\n\($vdiff)\n\n" +
   "TEMPLATE FILE CHANGES:\n\($tdiff)\n\n" +
   "EXISTING UPGRADE DOCS (mandatory reference for format, depth, and writing style):\n\($ex)\n\n" +
   "INSTRUCTIONS:\n" +
   "1. The first line must be exactly: \($tl)\n" +
   "2. \($sh)\n" +
   "3. Match the depth and style of the existing docs exactly:\n" +
   "   - For every changed value: show a before/after table (| Setting | v\($bv) | v\($nv) |)\n" +
   "   - For every new or modified config block: show a concrete YAML example with the exact keys and values\n" +
   "   - For removed fields: show what was removed and what operators should do instead\n" +
   "   - For template changes: explain what Kubernetes resource changed and the operational impact\n" +
   "   - Use callout blocks (> **Note:**, > **Warning:**) for important migration caveats\n" +
   "   - Include numbered migration steps when action is required from the operator\n" +
   "4. The second-to-last section must always be:\n## Preview changes before upgrading\n```bash\n\($diff)\n```\n> **Note:** Requires the [helm-diff plugin](https://github.com/databus23/helm-diff). Install with: `helm plugin install https://github.com/databus23/helm-diff`\n\n" +
   "5. The final section must always be:\n## Command to upgrade\n```bash\n\($cmd)\n```\n" +
   "6. Base content ONLY on what the diffs show. Do not invent changes not in the diff.\n" +
   "7. Output ONLY the markdown content. Do not wrap output in code fences."')

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
