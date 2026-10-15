<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>Environment Protection</h1></td>
  </tr>
</table>

> **Unreleased.** Until this ships in a release, reference it as `@develop` —
> `@v1` is the previous release and does not contain it yet.

Ensures a GitHub Environment exists and carries required reviewers — creating it
with the reviewers you name when it is missing.

## Why this exists

A job whose `environment:` names an Environment that does not exist **creates
it**, with no protection rules, and sails straight through. A gate built on that
Environment then reports green while gating nothing — the worst failure mode for
a control, because it looks like it is working and nobody goes looking.

Run this before any job that leans on an Environment as a human gate.

## What it does

| Situation | Result |
|---|---|
| Exists with required reviewers | Passes |
| Missing, `reviewers` given | **Creates it** with those reviewers and `Prevent self-review`, then reads it back to confirm |
| Missing, no `reviewers` | Fails — see below |
| Missing, `create-if-missing: false` | Fails |
| Missing, token cannot create | Fails, naming the permission |
| Exists **without** required reviewers | Fails, and is left alone — see below |
| Cannot be read at all (403) | Fails, and nothing is created |

### It never creates an unprotected Environment

An Environment with no reviewers approves itself. Creating one would produce the
exact failure this composite exists to prevent, so with no `reviewers` it fails
instead — telling you to pass them or to create the Environment by hand.

### It never rewrites an existing Environment

`PUT /repos/{owner}/{repo}/environments/{name}` replaces the **whole**
configuration. Repairing an unprotected Environment through it would silently
drop a wait timer or a deployment branch policy somebody set on purpose, so an
existing Environment is reported and left untouched. Creating from nothing is a
different act from overwriting somebody's configuration.

### One read, both answers

The rules and the reviewers come from a single `GET`. Two calls would allow a
state of "protected, reviewers unknown" — and an empty reviewer list is
indistinguishable from *this Environment has none*, so a caller naming the
approvers to a human would quietly fall back to whoever it had configured and
name the wrong people. With one read there is no such state: either both
answers are known, or the step fails.

### A 404 and a 403 are not the same

Only "does not exist" is this composite's to fix. If the Environment merely
cannot be read — a token without the scope — creating one on top would be
guessing, so it fails and says what it saw.

## Creation needs administration rights

`PUT .../environments/{name}` requires repository **administration** permission.
The default `GITHUB_TOKEN` does not have it, and `permissions:` cannot grant it —
`administration` is not a scope a workflow can request. Creation therefore works
only with a PAT or GitHub App token.

Without such a token, leave `create-if-missing: false` and create the Environment
by hand:

```bash
gh api --method PUT repos/<owner>/<repo>/environments/<name> --input - <<'JSON'
{"prevent_self_review": true, "reviewers": [{"type": "Team", "id": <team_id>}]}
JSON
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `github-token` | Token used to read, and to create when missing. Creation needs administration rights. | Yes | — |
| `environment` | Environment to ensure. | Yes | — |
| `repository` | Repository owning it, as `owner/name`. | No | `${{ github.repository }}` |
| `create-if-missing` | Create the Environment when it does not exist. | No | `true` |
| `reviewers` | Comma-separated `team:<slug>` or `user:<login>`. A bare value is read as a user. Empty means never create. | No | `''` |
| `prevent-self-review` | Set *Prevent self-review* on a created Environment. | No | `true` |
| `required-rule` | Protection rule that must be present. | No | `required_reviewers` |

`team:` takes the team **slug**, not the display name — `team:g_github_devops`,
not `team:G_Github_Devops`. Each entry costs one API lookup, because the
Environments API takes numeric ids only.

## Outputs

| Output | Description |
|--------|-------------|
| `protected` | `true` when the rule is present. The step fails before it could report `false`. |
| `created` | `true` when this run created the Environment. |
| `reviewers` | Who the Environment is actually gated by, as `team:<slug>`/`user:<login>`. Read back from the Environment, so it reflects one that already existed with different reviewers than were asked for. |

## Usage

```yaml
- name: Ensure the gate is real
  uses: LerianStudio/github-actions-shared-workflows/src/validate/environment-protection@v1
  with:
    github-token: ${{ secrets.MANAGE_TOKEN || github.token }}
    environment: breaking-approval
    reviewers: team:g_github_devops
```
