<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>helm-upgrade-doc</h1></td>
  </tr>
</table>

Reusable workflow that automatically generates an `UPGRADE-X.Y.md` operator guide after any Helm chart release. Triggered by stable tag pushes (e.g. `midaz-v6.5.0`, `plugin-br-pix-direct-jd-v2.2.9`), it extracts the chart name and version directly from the tag, diffs the chart between the previous stable tag and the current one, generates a structured upgrade guide via AI, and opens a PR for ops team review. Pre-release tags (`-beta`, `-rc`, `-alpha`, `-dev`, `-snapshot`) are automatically skipped.

## Features

- **Tag-driven**: Triggered by Semantic Release tag pushes — no manual configuration per chart
- **Auto-detection**: Extracts chart name and version from the tag (`plugin-br-pix-direct-jd-v2.2.9` → chart `plugin-br-pix-direct-jd`, version `2.2.9`)
- **Multi-provider AI**: Supports Anthropic API (`claude-sonnet-4-6`) or OpenRouter with configurable model
- **Bump-aware content**: Major includes Breaking Changes and Deployment Scenarios; minor includes Features and Configuration Reference; patch includes Fixes only
- **Rich diffs**: Full `values.yaml` diff (400 lines), full `templates/` diff (300 lines) with before/after YAML blocks
- **Few-shot consistency**: Loads the 2 most recent existing docs as style and format reference
- **PR with review**: Opens a PR against the default branch — no auto-merge, requires ops team review
- **Slack notification**: Notifies the ops team in Slack with the PR title and a direct review link
- **Idempotent**: Skips generation if the target doc already exists
- **GPG signing**: All commits are signed
- **Dry run mode**: Generates the doc and prints it to logs without opening a PR

## Naming convention

| Bump | Filename |
|------|----------|
| major (`4.x` → `5.0`) | `UPGRADE-5.0.md` |
| minor (`5.0` → `5.1`) | `UPGRADE-5.1.md` |
| patch (`5.1.0` → `5.1.1`) | `UPGRADE-5.1.1.md` |

## Usage

### Helm chart repository (minimal)

```yaml
name: Helm Upgrade Doc

on:
  push:
    tags:
      - '**-v[0-9]*'

jobs:
  upgrade-doc:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/helm-upgrade-doc.yml@v1
    secrets: inherit
```

### With custom chart structure

```yaml
jobs:
  upgrade-doc:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/helm-upgrade-doc.yml@v1
    with:
      charts_root: helm-charts
      docs_subdir: upgrade-guides
    secrets: inherit
```

### Dry run (preview without opening a PR)

```yaml
jobs:
  upgrade-doc:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/helm-upgrade-doc.yml@v1
    with:
      dry_run: true
    secrets: inherit
```

### Custom AI model via OpenRouter

```yaml
jobs:
  upgrade-doc:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/helm-upgrade-doc.yml@v1
    with:
      openai_model: anthropic/claude-opus-4
    secrets: inherit
```

## Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `runner_type` | string | `ubuntu-latest` | GitHub Actions runner to use |
| `charts_root` | string | `charts` | Root directory containing all charts |
| `docs_subdir` | string | `docs` | Subdirectory inside each chart where `UPGRADE-*.md` docs are stored |
| `openai_model` | string | `anthropic/claude-sonnet-4-5` | OpenRouter model for doc generation (ignored when `ANTHROPIC_API_KEY` is set) |
| `dry_run` | boolean | `false` | Generate the doc but skip opening the PR |

## Secrets

All secrets are passed via `secrets: inherit`. The caller repository must have the following secrets configured:

| Secret | Required | Description |
|--------|----------|-------------|
| `LERIAN_STUDIO_MIDAZ_PUSH_BOT_APP_ID` | Yes | GitHub App client ID for token generation |
| `LERIAN_STUDIO_MIDAZ_PUSH_BOT_PRIVATE_KEY` | Yes | GitHub App private key |
| `LERIAN_CI_CD_USER_GPG_KEY` | Yes | GPG private key for signing commits |
| `LERIAN_CI_CD_USER_GPG_KEY_PASSWORD` | Yes | GPG key passphrase |
| `LERIAN_CI_CD_USER_NAME` | Yes | Git committer name |
| `LERIAN_CI_CD_USER_EMAIL` | Yes | Git committer email |
| `ANTHROPIC_API_KEY` | No | Anthropic API key. When set, takes priority over OpenRouter |
| `OPENROUTER_API_KEY` | No | OpenRouter API key. Used when `ANTHROPIC_API_KEY` is not set |
| `SLACK_BOT_TOKEN_HELM` | No | Slack bot token for PR review notifications |
| `SLACK_CHANNEL_DEVOPS` | No | Slack channel ID to send notifications |
| `SLACK_GROUP_TECH_SUPPORT` | No | Slack group ID to mention in notifications (e.g. ops team) |

> **Note:** At least one of `ANTHROPIC_API_KEY` or `OPENROUTER_API_KEY` must be provided.

## Outputs

| Output | Description |
|--------|-------------|
| `doc-generated` | `"true"` when a new upgrade doc was generated, `"false"` if skipped |
| `doc-path` | Path to the generated file (empty when skipped) |
| `bump-type` | Version bump detected: `patch`, `minor`, `major`, or `none` |
| `new-version` | New chart version extracted from the tag (e.g. `2.2.9`) |
| `chart-name` | Chart name extracted from the tag (e.g. `plugin-br-pix-direct-jd`) |

## Required permissions in the caller job

```yaml
permissions:
  contents: write
  pull-requests: write
```

## How it works

1. **Create app token** — Generates a GitHub App token with `contents: write` and `pull-requests: write` permissions
2. **Detect version** — Parses the tag (`<chart-name>-v<version>`) to extract chart name and version; resolves the previous stable tag by scanning git history (skipping pre-release tags); computes bump type (major/minor/patch)
3. **Skip pre-releases** — Tags matching `-beta`, `-rc`, `-alpha`, `-dev`, or `-snapshot` exit immediately with `bump_type=none`
4. **Check idempotency** — Skips generation if `UPGRADE-X.Y.md` already exists in `<charts_root>/<chart>/<docs_subdir>/`
5. **Build diffs** — Runs `git diff <prev_tag>..<current_tag>` for `Chart.yaml` (full), `values.yaml` (first 400 lines), and `templates/` (first 300 lines)
6. **Load few-shot examples** — Reads the 2 most recent `UPGRADE-*.md` files from the docs directory as format and style reference
7. **Call AI** — Sends a structured prompt to Anthropic or OpenRouter; parses the response and strips any outer markdown wrapper
8. **Write doc** — Saves the file to `<charts_root>/<chart>/<docs_subdir>/UPGRADE-X.Y.md`, creating the directory if needed
9. **Open PR** — Commits (GPG-signed) and pushes to a new branch `release/upgrade-doc-<chart>-v<version>`, then opens a PR against the default branch for review
10. **Notify Slack** — Sends a message to the ops channel with the PR title and a direct review link (skipped if Slack secrets are not set)

## Generated doc structure

The AI prompt enforces a consistent structure based on the bump type:

### Major
- Topics (ToC with bold links)
- Breaking Changes
- Features (numbered subsections)
- Deployment Scenarios
- Configuration Reference (full YAML + Flag/Default/Description table)
- Preview changes before upgrading
- Command to upgrade

### Minor
- Topics (ToC with bold links)
- Features (numbered subsections)
- Configuration Reference (if new fields added)
- Breaking Changes (only if detected)
- Preview changes before upgrading
- Command to upgrade

### Patch
- Topics (ToC with bold links)
- Fixes
- Preview changes before upgrading
- Command to upgrade

All YAML snippets use ` ```yaml ` code blocks, all commands use ` ```bash ` code blocks, and before/after comparisons use labeled pairs.

## Notes

- The workflow integrates with Semantic Release: `release.yml` bumps `Chart.yaml`, creates the tag, which triggers `helm-upgrade-doc.yml`
- The `paths-ignore` in `release.yml` must include `**/docs/**` to prevent upgrade doc commits from triggering a new release cycle
- Tag format must be `<chart-name>-v<semver>` (e.g. `midaz-v6.5.0`, `plugin-access-manager-v1.2.0`)
- Charts named `plugin-access-manager` or `otel-collector-lerian` use their own name as the OCI package name; all others append `-helm` (e.g. `midaz-helm`)
- The PR branch is named `release/upgrade-doc-<chart>-v<version>` and is deleted after merge

## Related

- [gptchangelog](gptchangelog-workflow.md) — AI-powered CHANGELOG.md generation after release
- [helm-upgrade-doc composite](../src/docs/helm-upgrade-doc/README.md) — Composite action reference
