<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>GitHub Actions Shared Workflows</h1></td>
  </tr>
</table>

Centralized reusable GitHub Actions workflows and composite actions for the Lerian organization.

## How it works

```
Your repository workflow
         ↓
Reusable workflow (.github/workflows/*.yml)   ← orchestrates jobs
         ↓
Composite action  (src/<capability>/<name>/)  ← encapsulates steps
```

Workflows are called via `workflow_call` and versioned with semantic tags. Pin to a specific tag in production — never use `@main`.

## Available workflows

See the [`docs/`](docs/) directory for the full list, inputs, outputs, and usage examples for each workflow.

## Quick Start

```yaml
jobs:
  security:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-security-scan.yml@v1.2.3

  release:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/release.yml@v1.2.3

  gitops:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@v1.2.3
```

## Versioning

Releases follow [Semantic Versioning](https://semver.org/) via [semantic-release](https://github.com/semantic-release/semantic-release):

- Merges to `develop` → beta pre-release (`v1.2.3-beta.1`)
- Merges to `main` → stable release (`v1.2.3`)

## AI Assistant Support

Built-in guidance for AI assistants is included so they understand the architecture before making changes.

### Cursor IDE

Rules activate automatically based on the file open — no setup needed.

| File | Rule loaded |
|---|---|
| `src/**/*.yml` | Composite action conventions |
| `.github/workflows/*.yml` | Reusable workflow architecture |

### Claude Code CLI

```bash
claude
> /workflow    # reusable workflow rules
> /composite   # composite action rules
> /gha         # everything at once
```

**Example:**
```bash
claude
> /gha
> Add a helm-deploy composite under src/deploy/ and wire it into release.yml
```

Commands live in `.claude/commands/`. Rules live in `.cursor/rules/`.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) for branch strategy, commit conventions, and the PR process.

## Security

Report vulnerabilities privately — see [SECURITY.md](SECURITY.md). Do not open public issues.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
