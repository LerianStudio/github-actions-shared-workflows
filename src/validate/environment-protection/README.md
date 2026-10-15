<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>Environment Protection</h1></td>
  </tr>
</table>

Fails when a GitHub Environment is missing or carries no required reviewers.

## Why this exists

A job whose `environment:` names an Environment that does not exist **creates
it**, with no protection rules, and sails straight through. A gate built on that
Environment then reports green while gating nothing — the worst failure mode for
a control, because it looks like it is working and nobody goes looking.

Run this before any job that leans on an Environment as a human gate.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `github-token` | Token used to read the Environment. Needs read access to the repository. | Yes | — |
| `environment` | Environment whose protection rules are checked. | Yes | — |
| `repository` | Repository owning it, as `owner/name`. | No | `${{ github.repository }}` |
| `required-rule` | Protection rule type that must be present. | No | `required_reviewers` |

## Outputs

| Output | Description |
|--------|-------------|
| `protected` | `true` when the rule is present. The step fails before it could report `false`, so a caller reading this output is reading `true`. |

## Failure modes, and what they mean

| Situation | Result |
|---|---|
| Environment missing | Fails — the message says to create it with required reviewers |
| Environment exists, no required reviewers | Fails — names the rules it does have |
| API read blocked by token scope | Fails — indistinguishable from "missing" from here, so it fails closed |

That last row is deliberate. A caller that genuinely cannot read the API, and
knows the Environment is configured, should skip this step rather than have it
pass on an unverified assumption.

## Usage

```yaml
- name: Verify the gate is real
  uses: LerianStudio/github-actions-shared-workflows/src/validate/environment-protection@v1
  with:
    github-token: ${{ secrets.MANAGE_TOKEN || github.token }}
    environment: breaking-approval
```

## Setting the Environment up

```bash
gh api --method PUT repos/<owner>/<repo>/environments/<name> --input - <<'JSON'
{"prevent_self_review": true, "reviewers": [{"type": "Team", "id": <team_id>}]}
JSON
```

`prevent_self_review` matters as much as the reviewers: without it the person who
opened the pull request can approve their own gate.
