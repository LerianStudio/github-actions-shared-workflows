<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>tier-promote</h1></td>
  </tr>
</table>

Promotes one already-resolved stable commit into **one** tier branch of this repository. The orchestration — order, approvals, concurrency — lives in [`.github/workflows/tier-promotion.yml`](../../../.github/workflows/tier-promotion.yml); this composite performs a single step of it.

## Inputs

| Input | Required | Default | Description |
|---|:---:|---|---|
| `tier` | Yes | — | Tier branch to promote into. Must match `^tier-[0-9]+$` |
| `tag` | Yes | — | Stable tag being promoted. Must match `^v\d+\.\d+\.\d+$` |
| `source-sha` | Yes | — | Full 40-char commit the tag resolved to, pinned by the caller for the whole train |
| `config` | No | `config/tier-promotion.yml` | Flow config, read for this tier's `auto_merge_pr_fallback` |
| `dry-run` | No | `false` | Report the intended change without writing |
| `github-token` | Yes | — | Needs `contents:write` and `pull-requests:write`. Typically a GitHub App installation token — see [Token](#token) |

## Outputs

| Output | Description |
|---|---|
| `has-promotion` | `'true'` only when the tier branch was moved by a direct push. `'false'` on a no-op, a dry run, or an open fallback PR — see the note below |
| `action` | `push`, `pr`, `skip` (tier already carried this tree) or `dry-run` |
| `url` | PR URL when the fallback opened one, empty otherwise |
| `commit` | Resulting commit on the tier branch |

`has-promotion` answers one question only: **does the tier branch now carry the promoted tree?** The PR fallback does not update the tier — it updates `promote/<tier>/<tag>` and opens a pull request, and the tier is unchanged until that merges. So the fallback reports `has-promotion: false` with `action: pr` and a `url`. A caller announcing "tier-1 now runs vX" must gate on `has-promotion`; one that wants to chase a pending promotion should look at `action` and `url`.

## Usage

### As a composite step

> **This example is repository-local.** It resolves the composite through `uses: ./src/config/tier-promote`, which only works from a workflow inside `github-actions-shared-workflows` — the checkout at `github.workflow_sha` materializes this repository's tree in the workspace. External callers cannot use this form, and are not meant to: the tier branches, the flow config and the Environments all live here. Use the reusable workflow below instead.

The caller must configure the signing identity first — the `tier-rule` ruleset requires signed commits on `refs/heads/tier-*`, and this composite deliberately does not set it (see [Signing](#signing)).

```yaml
jobs:
  promote:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    environment: tier-0
    permissions:
      contents: read
    steps:
      - name: Checkout shared-workflows
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v6
        with:
          ref: ${{ github.workflow_sha }}

      - uses: actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1 # v3.2.0
        id: app-token
        with:
          client-id: ${{ secrets.LERIAN_STUDIO_MIDAZ_PUSH_BOT_APP_ID }}
          private-key: ${{ secrets.LERIAN_STUDIO_MIDAZ_PUSH_BOT_PRIVATE_KEY }}

      - name: Import GPG key
        uses: crazy-max/ghaction-import-gpg@2dc316deee8e90f13e1a351ab510b4d5bc0c82cd # v7
        with:
          gpg_private_key: ${{ secrets.LERIAN_CI_CD_USER_GPG_KEY }}
          passphrase: ${{ secrets.LERIAN_CI_CD_USER_GPG_KEY_PASSWORD }}
          git_committer_name: ${{ secrets.LERIAN_CI_CD_USER_NAME }}
          git_committer_email: ${{ secrets.LERIAN_CI_CD_USER_EMAIL }}
          git_config_global: true
          git_user_signingkey: true
          git_commit_gpgsign: true

      - name: Promote
        id: promote
        uses: ./src/config/tier-promote
        with:
          tier: tier-0
          tag: v1.2.3
          source-sha: ${{ needs.resolve.outputs.sha }}
          dry-run: false
          github-token: ${{ steps.app-token.outputs.token }}

      - name: Notify
        if: steps.promote.outputs.has-promotion == 'true'
        run: echo "tier-0 now carries ${{ steps.promote.outputs.commit }}"
```

### As a reusable workflow

Prefer this over calling the composite directly — the workflow owns the tier ordering, the approval gates and the per-tier concurrency groups:

```yaml
jobs:
  promote-tiers:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/tier-promotion.yml@v1.2.3
    with:
      tag: v1.2.3
      dry_run: false
    secrets: inherit
```

For testing, point at a branch instead: `@develop` or `@feat/<branch>`.

## Permissions required

The job needs no elevated `GITHUB_TOKEN` — every write goes through `github-token`:

```yaml
permissions:
  contents: read
```

The token passed as `github-token` needs, on this repository:

| Scope | Why |
|---|---|
| `contents: write` | Push the promotion commit to the tier branch |
| `pull-requests: write` | Open or reuse the fallback PR when the direct push is rejected |

### Token

Use a **GitHub App installation token**, not a PAT. An App identity can be granted ruleset bypass on its own, which is what allows `refs/heads/tier-*` to require a pull request from everyone else while the promotion still pushes directly. Granting that exemption to a team of humans instead would defeat the requirement.

It also cannot be `GITHUB_TOKEN`: a pull request opened by it does not trigger workflows, so the fallback PR would carry no checks.

```yaml
- uses: actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1 # v3.2.0
  id: app-token
  with:
    client-id: ${{ secrets.LERIAN_STUDIO_MIDAZ_PUSH_BOT_APP_ID }}
    private-key: ${{ secrets.LERIAN_STUDIO_MIDAZ_PUSH_BOT_PRIVATE_KEY }}
```

## How it promotes

```
git clone --branch <tier>          # throwaway clone, not the job workspace
git fetch origin refs/tags/<tag>
git read-tree --reset -u <sha>     # tier tip stays HEAD; tree becomes <sha>'s
git commit                         # exactly one commit, tree IS the promoted tree
git push origin HEAD:<tier>        # on failure → push branch + open PR
```

Three properties fall out of this shape:

**No merge, so no conflict.** The tier branches are expected to diverge in content from `main` once the self-reference rewrite lands. A merge would then conflict on precisely those lines, on every promotion. Materializing the tree wholesale cannot conflict.

**Always a fast-forward.** A commit on top of the tier tip satisfies the `non_fast_forward` rule the `tier-rule` ruleset enforces on `refs/heads/tier-*`. A moved ref would not.

**Rollback needs no bypass.** Promoting an older tag lands as a new forward commit carrying the older tree, so nothing is ever force-pushed.

Idempotent: if the tier tip already carries the promoted tree, the run reports `skip` and writes nothing.

## Guards

- `tier`, `tag` and `source-sha` are validated by shape before anything runs, and reach the shell through `env:` rather than `${{ }}` interpolation, so a crafted value cannot break out.
- The tier must be declared in the flow config.
- The tag is re-resolved inside the clone and compared to `source-sha`. If the tag moved between the caller opening the train and this job running, the promotion is refused rather than promoting a different tree than the one reviewed.

## Signing

The `tier-rule` ruleset requires signed commits, so the **caller** must configure the signing identity globally before invoking this composite — see the `crazy-max/ghaction-import-gpg` step in `tier-promotion.yml`. This composite deliberately does not set `user.name`, `user.email` or signing config: doing so would replace the identity the caller established.

## Notes

- Work happens in a throwaway clone under `mktemp -d`, never in the job workspace. The workspace holds this composite's own scripts, and replacing the working tree underneath a running script is a good way to produce inexplicable failures.
- `[skip ci]` is added on the direct-push path (nothing in this repo triggers on a push to `tier-*`) and amended away on the PR path, where skipped checks would leave the PR unmergeable.
