<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>update-major-tag</h1></td>
  </tr>
</table>

Force-update the floating major version tag (e.g. `v1`) to point at the latest stable `vX.Y.Z` tag in the repository. Intended to run after a successful stable release so callers can pin composite actions to `@v1` and always resolve to the latest stable release.

### Behavior

1. Fetches all tags from the remote.
2. Finds the greatest stable tag matching `^v[0-9]+\.[0-9]+\.[0-9]+$` (pre-release tags like `-beta.N` / `-rc.N` are ignored).
3. Derives the major prefix (`v1.26.0 → v1`).
4. If the major tag already points at the resolved commit, exits with a notice — idempotent.
5. Otherwise, creates/moves the major tag as an annotated tag and force-pushes it.

### Assumptions

- The caller has already checked out the repository with `fetch-depth: 0` (so all tags are reachable).
- The checkout was authenticated with a token that has permission to push tags (typically via `actions/checkout@... with.token:`).
- For signed tags, the caller has imported a GPG key and enabled `git_tag_gpgsign` (`git tag -a` will auto-sign when `tag.gpgSign=true` is set globally).

## Inputs

_None._ All behavior is derived from the repository's tag list.

## Usage

```yaml
jobs:
  update-major-tag:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/create-github-app-token@<sha> # v3.1.1
        id: app-token
        with:
          client-id: ${{ secrets.APP_ID }}
          private-key: ${{ secrets.APP_PRIVATE_KEY }}

      - uses: actions/checkout@<sha> # v6
        with:
          fetch-depth: 0
          token: ${{ steps.app-token.outputs.token }}

      - uses: crazy-max/ghaction-import-gpg@<sha> # v7
        with:
          gpg_private_key: ${{ secrets.GPG_KEY }}
          passphrase: ${{ secrets.GPG_PASSPHRASE }}
          git_committer_name: ${{ secrets.CI_USER_NAME }}
          git_committer_email: ${{ secrets.CI_USER_EMAIL }}
          git_config_global: true
          git_user_signingkey: true
          git_tag_gpgsign: true

      - uses: LerianStudio/github-actions-shared-workflows/src/config/update-major-tag@v1
```

## Required permissions

```yaml
permissions:
  contents: write
```
