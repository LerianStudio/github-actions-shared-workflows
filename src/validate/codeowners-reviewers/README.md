<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>CODEOWNERS Reviewers</h1></td>
  </tr>
</table>

Derives an Environment reviewer list from a repository's CODEOWNERS.

The people who own the code are the people who should answer a gate about it,
and CODEOWNERS is where a repository already states that. Deriving from it means
a gate shipped to a hundred repositories asks each one's own owners, with
nothing to configure and nothing to keep in sync.

```
*    @LerianStudio/g_github_devops      →    team:g_github_devops
```

## It reads the base ref

Pass the pull request's **base** branch. A CODEOWNERS taken from the head would
let an author edit who is allowed to approve their own change — which is the one
thing an approval gate cannot permit.

It also reads through the API rather than the working tree, so the calling job
needs no checkout.

## Which rule it takes

The catch-all `*` by default, because that is what a repository-wide gate should
ask. Pass `pattern` for a narrower one.

Where CODEOWNERS has several matching rules the **last** one wins, which is how
GitHub itself resolves them.

Lookup order for the file matches GitHub's: `.github/CODEOWNERS`, then
`CODEOWNERS`, then `docs/CODEOWNERS`.

## What it drops, and says so

| Owner | Result |
|---|---|
| `@org/team` | `team:team` |
| `@user` | `user:user` |
| `someone@example.com` | Dropped — an email does not resolve to a reviewer here |
| Beyond `max-reviewers` | Dropped — an Environment accepts six |

Both are reported to the step log rather than truncated quietly. A gate narrower
than the repository declared is worth a line in the log.

## It never fails on absence

No CODEOWNERS, no matching rule, or only owners that cannot be reviewers all
produce `found=false` and an empty list — not an error. Whether that should
block is the caller's decision, not this composite's.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `github-token` | Token used to read CODEOWNERS. Needs `contents: read`. | Yes | — |
| `repository` | Repository whose CODEOWNERS is read. | No | `${{ github.repository }}` |
| `ref` | Ref to read from. Pass the pull request base. Empty reads the default branch. | No | `''` |
| `pattern` | CODEOWNERS pattern whose owners are taken. | No | `*` |
| `max-reviewers` | Most reviewers to return. | No | `6` |

## Outputs

| Output | Description |
|--------|-------------|
| `found` | Whether any reviewer could be derived (`true`/`false`). |
| `reviewers` | Comma-separated `team:<slug>` / `user:<login>`, ready for `environment-protection`. |
| `source` | Which CODEOWNERS was read. |

## Usage

```yaml
- name: Derive the reviewers
  id: codeowners
  uses: LerianStudio/github-actions-shared-workflows/src/validate/codeowners-reviewers@v1
  with:
    github-token: ${{ secrets.MANAGE_TOKEN || github.token }}
    ref: ${{ github.event.pull_request.base.ref }}

- name: Ensure the gate is real
  uses: LerianStudio/github-actions-shared-workflows/src/validate/environment-protection@v1
  with:
    github-token: ${{ secrets.MANAGE_TOKEN || github.token }}
    environment: breaking-approval
    reviewers: ${{ steps.codeowners.outputs.reviewers }}
```

## Local test

```bash
bash src/validate/codeowners-reviewers/test.sh
```

22 cases against a stubbed `gh`: both owner forms, comments and trailing
comments, last-rule-wins, Enterprise section headers, the three file locations,
the reviewer cap, and every shape that yields nothing. Includes the case that
caught a real bug — an unquoted `${line}` split also globs, and `*` is the most
common pattern in any CODEOWNERS.
