<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>helm-upgrade-doc</h1></td>
  </tr>
</table>

Reusable workflow that generates an `UPGRADE-X.Y.md` guide for Helm chart PRs using AI via OpenRouter. Detects the version bump type (patch, minor, major) from `Chart.yaml`, builds a structured diff of `values.yaml` and `templates/`, uses the two most recent existing upgrade docs as few-shot examples, and commits the generated file directly to the PR branch with a GPG-signed commit. Skips generation when the doc already exists — safe to re-run on subsequent pushes.

## Features

- **AI-powered doc generation**: Uses OpenRouter API with configurable model (default: `anthropic/claude-sonnet-4-5`)
- **Bump-aware content**: Major bumps include Breaking Changes and Migration Steps; minor includes Features; patch includes Fixes only
- **Few-shot format consistency**: Loads the 2 most recent existing docs as style reference
- **Idempotent**: Skips generation if the target `UPGRADE-X.Y.md` already exists
- **GPG signing**: All commits are signed
- **Dry run mode**: Generates the doc and prints it to logs without committing

## Naming convention

| Bump | Filename |
|------|----------|
| major (5.x → 6.x) | `UPGRADE-6.0.md` |
| minor (6.0 → 6.1) | `UPGRADE-6.1.md` |
| patch (6.1.0 → 6.1.1) | `UPGRADE-6.1.1.md` |

## Usage

### Helm chart repository (recommended)

```yaml
name: Helm Upgrade Doc

on:
  pull_request:
    types: [opened, synchronize, reopened]
    paths:
      - 'charts/midaz/Chart.yaml'
      - 'charts/midaz/values.yaml'
      - 'charts/midaz/templates/**'

permissions:
  contents: write
  pull-requests: write

jobs:
  upgrade-doc:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/helm-upgrade-doc.yml@v1
    secrets: inherit
```

### Custom chart path

```yaml
jobs:
  upgrade-doc:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/helm-upgrade-doc.yml@v1
    with:
      chart_path: charts/my-chart
      docs_path: charts/my-chart/docs
    secrets: inherit
```

### Dry run (preview without committing)

```yaml
jobs:
  upgrade-doc:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/helm-upgrade-doc.yml@v1
    with:
      dry_run: true
    secrets: inherit
```

### Custom model

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
|---|---|---|---|
| `runner_type` | string | `blacksmith-4vcpu-ubuntu-2404` | GitHub runner type |
| `chart_path` | string | `charts/midaz` | Path to the Helm chart directory |
| `docs_path` | string | `charts/midaz/docs` | Path to the docs directory |
| `openai_model` | string | `anthropic/claude-sonnet-4-5` | OpenRouter model for generation |
| `dry_run` | boolean | `false` | Preview without committing |

## Secrets

All secrets are passed via `secrets: inherit`. Required in the caller repository:

| Secret | Description |
|---|---|
| `LERIAN_STUDIO_MIDAZ_PUSH_BOT_APP_ID` | GitHub App client ID for token generation |
| `LERIAN_STUDIO_MIDAZ_PUSH_BOT_PRIVATE_KEY` | GitHub App private key |
| `LERIAN_CI_CD_USER_GPG_KEY` | GPG private key for signing commits |
| `LERIAN_CI_CD_USER_GPG_KEY_PASSWORD` | GPG key passphrase |
| `LERIAN_CI_CD_USER_NAME` | Git committer name |
| `LERIAN_CI_CD_USER_EMAIL` | Git committer email |
| `OPENROUTER_API_KEY` | OpenRouter API key |

## How it works

1. **Detect bump type** — Compares `Chart.yaml` version between the base branch and the PR branch
2. **Check idempotency** — Skips if `UPGRADE-X.Y.md` already exists in `docs/`
3. **Build diff context** — Extracts `Chart.yaml` diff, `values.yaml` diff (first 400 lines), and template file changes
4. **Load few-shot examples** — Reads the 2 most recent existing `UPGRADE-*.md` files as format reference
5. **Call OpenRouter** — Sends a structured prompt; parses the markdown response
6. **Commit** — Writes the file and pushes directly to the PR branch (GPG-signed, `[skip ci]`)

## Workflow jobs

### generate-upgrade-doc

Creates the GitHub App token and calls the `src/docs/helm-upgrade-doc` composite action.

## Related

- [gptchangelog](gptchangelog-workflow.md) — AI-powered CHANGELOG.md generation after release
- [helm-update-chart](../src/docs/helm-upgrade-doc/README.md) — Composite action reference
