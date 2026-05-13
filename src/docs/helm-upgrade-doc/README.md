<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>helm-upgrade-doc</h1></td>
  </tr>
</table>

Generates an `UPGRADE-X.Y.md` guide for Helm chart PRs using OpenRouter AI. Detects the version bump type (patch, minor, major) from `Chart.yaml`, builds a structured diff of `values.yaml` and templates, uses existing upgrade docs as few-shot examples, and commits the generated file directly to the PR branch with a GPG-signed commit. Skips generation when the doc already exists — safe to re-run on subsequent pushes to the same PR.

## Inputs

| Input | Description | Required | Default |
|---|---|---|---|
| `github-token` | GitHub token with `contents: write` and `pull-requests: write` | yes | — |
| `gpg-private-key` | GPG private key for signing commits | yes | — |
| `gpg-passphrase` | Passphrase for the GPG private key | yes | — |
| `git-committer-name` | Git committer name for signed commits | yes | — |
| `git-committer-email` | Git committer email for signed commits | yes | — |
| `openrouter-api-key` | OpenRouter API key for AI doc generation | yes | — |
| `base-ref` | Base branch ref to diff against (e.g. `main`, `develop`) | yes | — |
| `chart-path` | Path to the Helm chart directory | no | `charts/midaz` |
| `docs-path` | Path to the docs directory where UPGRADE docs are stored | no | `charts/midaz/docs` |
| `openai-model` | OpenRouter model to use for generation | no | `anthropic/claude-sonnet-4-5` |
| `dry-run` | Generate the doc but skip committing it to the branch | no | `false` |

## Outputs

| Output | Description |
|---|---|
| `doc-generated` | `'true'` if a new upgrade doc was generated and committed |
| `doc-path` | Path to the generated doc (empty if not generated) |
| `bump-type` | Version bump detected: `patch`, `minor`, `major`, or `none` |
| `new-version` | New chart version from `Chart.yaml` |

## Usage as composite step

```yaml
jobs:
  upgrade-doc:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - name: Create GitHub App Token
        uses: actions/create-github-app-token@1b10c78c7865c340bc4f6099eb2f838309f1e8c3 # v3.1.1
        id: app-token
        with:
          client-id: ${{ secrets.LERIAN_STUDIO_MIDAZ_PUSH_BOT_APP_ID }}
          private-key: ${{ secrets.LERIAN_STUDIO_MIDAZ_PUSH_BOT_PRIVATE_KEY }}

      - name: Generate Helm Upgrade Doc
        uses: LerianStudio/github-actions-shared-workflows/src/docs/helm-upgrade-doc@v1
        with:
          github-token: ${{ steps.app-token.outputs.token }}
          gpg-private-key: ${{ secrets.LERIAN_CI_CD_USER_GPG_KEY }}
          gpg-passphrase: ${{ secrets.LERIAN_CI_CD_USER_GPG_KEY_PASSWORD }}
          git-committer-name: ${{ secrets.LERIAN_CI_CD_USER_NAME }}
          git-committer-email: ${{ secrets.LERIAN_CI_CD_USER_EMAIL }}
          openrouter-api-key: ${{ secrets.OPENROUTER_API_KEY }}
          base-ref: ${{ github.base_ref || 'main' }}
```

## Usage via reusable workflow

```yaml
jobs:
  upgrade-doc:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/helm-upgrade-doc.yml@v1
    secrets: inherit
```

## Required permissions

```yaml
permissions:
  contents: write
  pull-requests: write
```
