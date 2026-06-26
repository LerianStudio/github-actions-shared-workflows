<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>gptchangelog</h1></td>
  </tr>
</table>

Generates `CHANGELOG.md` files using GPT (via OpenRouter) and pushes a signed commit directly to the default branch. Backmerges into `develop` automatically; falls back to a PR only when a conflict prevents the direct push. Supports both single-app and monorepo layouts. Skips prerelease tags when `stable-releases-only` is enabled.

Bot commits (any login ending in `[bot]` plus the entries in `bot-ignore-list`) and `[skip ci]` commits (semantic-release version bumps, changelog backmerges, etc.) are filtered out before the GPT prompt is built, ensuring the changelog only reflects meaningful human-authored changes.

## Inputs

| Input | Description | Required | Default |
|---|---|---|---|
| `github-token` | GitHub token with `contents: write` and `pull-requests: write` | yes | — |
| `gpg-private-key` | GPG private key for signing commits | yes | — |
| `gpg-passphrase` | Passphrase for the GPG private key | yes | — |
| `git-committer-name` | Git committer name for signed commits | yes | — |
| `git-committer-email` | Git committer email for signed commits | yes | — |
| `openrouter-api-key` | OpenRouter API key for GPT changelog generation | yes | — |
| `filter-paths` | Newline-separated path prefixes for monorepo support. Empty = single-app mode. | no | `''` |
| `stable-releases-only` | Skip beta/rc/alpha tags | no | `'true'` |
| `openai-model` | Model to use (OpenRouter format) | no | `'openai/gpt-4o'` |
| `bot-ignore-list` | Additional space-separated GitHub login substrings to exclude. Logins ending in `[bot]` are always excluded. A built-in baseline (`dependabot renovate github-actions lerian-studio-midaz-push-bot semantic-release-bot`) is always applied; this value extends it. | no | `''` |

## Outputs

| Output | Description |
|---|---|
| `has-changes` | `'true'` if the composite identified apps eligible for changelog generation |
| `apps-updated` | Comma-separated list of apps whose CHANGELOGs were updated (empty if none) |

## Usage as composite step

```yaml
jobs:
  changelog:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - name: Create GitHub App Token
        uses: actions/create-github-app-token@1b10c78c7865c340bc4f6099eb2f838309f1e8c3 # v3.1.1
        id: app-token
        with:
          client-id: ${{ secrets.LERIAN_STUDIO_MIDAZ_PUSH_BOT_APP_ID }}
          private-key: ${{ secrets.LERIAN_STUDIO_MIDAZ_PUSH_BOT_PRIVATE_KEY }}

      - name: Generate Changelog
        uses: LerianStudio/github-actions-shared-workflows/src/changelog/gptchangelog@v1
        with:
          github-token: ${{ steps.app-token.outputs.token }}
          gpg-private-key: ${{ secrets.LERIAN_CI_CD_USER_GPG_KEY }}
          gpg-passphrase: ${{ secrets.LERIAN_CI_CD_USER_GPG_KEY_PASSWORD }}
          git-committer-name: ${{ secrets.LERIAN_CI_CD_USER_NAME }}
          git-committer-email: ${{ secrets.LERIAN_CI_CD_USER_EMAIL }}
          openrouter-api-key: ${{ secrets.OPENROUTER_API_KEY }}
```

## Usage via reusable workflow (with changelog enabled)

```yaml
jobs:
  release:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/release.yml@develop
    with:
      enable_changelog: true
      stable_releases_only: true
    secrets: inherit
```

## Required permissions

```yaml
permissions:
  contents: write
  pull-requests: write
```
