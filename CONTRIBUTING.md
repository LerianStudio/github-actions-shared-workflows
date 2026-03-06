<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>Contributing</h1></td>
  </tr>
</table>

Thank you for contributing to the Lerian shared workflows repository. Changes here affect every repository across the organization, so we hold contributions to a high standard. Please read this guide carefully before opening a PR.

---

## Table of Contents

- [Branch Strategy](#branch-strategy)
- [Merge Strategy](#merge-strategy)
- [Step-by-Step Contribution Flow](#step-by-step-contribution-flow)
- [Commit Message Format](#commit-message-format)
- [Testing Workflow Changes](#testing-workflow-changes)
- [Release Process](#release-process)
- [Repository Structure](#repository-structure)
- [Important Rules](#important-rules)
- [Getting Help](#getting-help)

---

## Branch Strategy

This repository uses a two-branch model:

| Branch | Purpose | Release type |
|---|---|---|
| `main` | Stable, production-ready code | `v1.2.3` |
| `develop` | Integration and pre-release testing | `v1.2.3-beta.N` |

**Working branches** are short-lived and always merged into `develop` first:

| Prefix | When to use | Example |
|---|---|---|
| `feature/` | New workflow or new capability in an existing one | `feature/add-helm-lint-step` |
| `fix/` | Bug fix in a workflow | `fix/gitops-missing-env-var` |
| `hotfix/` | Urgent fix that must go to `main` as fast as possible | `hotfix/v1.3.1-broken-release` |
| `docs/` | Documentation-only changes | `docs/update-go-ci-examples` |
| `chore/` | Maintenance — dependency bumps, config updates | `chore/bump-actions-checkout-v5` |

> **Never commit directly to `main` or `develop`.** All changes must go through a PR.

---

## Merge Strategy

The merge strategy varies by the type of PR. This is a **convention enforced by reviewers** — it is not locked at the settings level to allow flexibility for backmerges and releases.

| PR type | Source → Target | Strategy | Why |
|---|---|---|---|
| Feature / fix / docs | `feature/*` → `develop` | **Squash and merge** | One clean commit per PR; drives semantic-release correctly |
| Release | `develop` → `main` | **Merge commit** | Preserves individual PR commits so semantic-release can compute the version bump |
| Hotfix | `hotfix/*` → `main` | **Squash and merge** | One clean commit for the fix; backmerge follows immediately |
| Backmerge | `main` → `develop` | **Merge commit** | Preserves history; squash would collapse all of main into one commit |

> **Reviewers:** before clicking Merge, confirm the correct strategy is selected in the GitHub UI. Do not use rebase.

---

## Step-by-Step Contribution Flow

This repository is public. The contribution flow differs slightly depending on whether you are a **Lerian team member** (write access) or an **external contributor** (no write access).

### 1. Set up your working branch

**Lerian team members — branch directly:**

```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
```

> **Hotfixes only:** branch from `main` if the fix must bypass `develop`.
> ```bash
> git checkout main && git pull origin main
> git checkout -b hotfix/description
> ```

**External contributors — fork first:**

```bash
# 1. Fork the repo on GitHub (click "Fork" on the repo page)
# 2. Clone your fork
git clone https://github.com/<your-username>/github-actions-shared-workflows.git
cd github-actions-shared-workflows

# 3. Add the upstream remote
git remote add upstream https://github.com/LerianStudio/github-actions-shared-workflows.git

# 4. Branch from upstream/develop
git fetch upstream
git checkout -b feature/your-feature-name upstream/develop
```

When opening the PR, target the `develop` branch of the **upstream** (`LerianStudio`) repository — not your fork's `main`.

### 2. Make your changes

- Edit only the workflow file(s) relevant to your change
- Follow YAML best practices (2-space indent, quoted strings for expressions)
- Add inline comments for non-obvious steps or conditions
- Update the corresponding doc in `docs/` if behavior or inputs/outputs changed
- Update `README.md` if a new workflow was added or a key feature changed

### 3. Commit using Conventional Commits

All commit messages must follow the [Conventional Commits](https://www.conventionalcommits.org/) specification. This drives automatic versioning — **the type you choose determines the version bump**.

```
<type>(<scope>): <subject>

[optional body]

[optional footer — BREAKING CHANGE: ...]
```

**Subject rules:**
- Start with a lowercase letter
- Use the imperative mood ("add support" not "adds support" or "added support")
- No period at the end
- Maximum 72 characters

#### Types and version impact

| Type | Description | Version bump |
|---|---|---|
| `feat` | New workflow or new input/output/behavior | Minor (`1.x.0`) |
| `fix` | Bug fix in a workflow step or condition | Patch (`1.0.x`) |
| `perf` | Performance improvement (caching, parallelism) | Minor (`1.x.0`) |
| `refactor` | Internal restructuring, no behavior change | Minor (`1.x.0`) |
| `build` | Build system or tooling changes | Minor (`1.x.0`) |
| `docs` | Documentation only | Patch (`1.0.x`) |
| `chore` | Dependency bumps, config maintenance | Patch (`1.0.x`) |
| `ci` | Changes to self-CI workflows | Patch (`1.0.x`) |
| `test` | Adding or updating tests | Patch (`1.0.x`) |
| `BREAKING CHANGE` | Callers must update their configuration | Major (`x.0.0`) |

#### Scopes (optional but recommended)

Use a scope to identify the affected workflow or area:

| Scope | Workflow |
|---|---|
| `go-ci` | Go CI workflow |
| `go-security` | Go Security workflow |
| `go-release` | Go Release workflow |
| `go-pr-analysis` | Go PR Analysis workflow |
| `gitops` | GitOps Update workflow |
| `e2e` | API Dog E2E Tests workflow |
| `pr-validation` | PR Validation workflow |
| `pr-security` | PR Security Scan workflow |
| `release` | Release workflow |
| `changed-paths` | Changed Paths workflow |
| `build` | Build workflow |
| `slack` | Slack Notify workflow |
| `frontend` | Frontend PR Analysis workflow |
| `gptchangelog` | GPT Changelog workflow |
| `helm` | Helm Update / Dispatch workflows |
| `typescript` | TypeScript CI / Release workflows |
| `docs` | Documentation |
| `deps` | Dependency updates |

**Examples:**

```bash
# New feature with scope
git commit -m "feat(gitops): add sandbox environment support"

# Bug fix without scope
git commit -m "fix: resolve yq checksum verification on arm64 runners"

# Breaking change
git commit -m "feat(go-ci): replace golangci_lint_args with lint_config_path input

BREAKING CHANGE: The golangci_lint_args input has been removed.
Callers must switch to lint_config_path pointing to their .golangci.yml."
```

### 4. Push and open a PR to `develop`

```bash
git push origin feature/your-feature-name
```

Open a Pull Request targeting **`develop`**. Use the PR template — fill in the affected workflows table and the input/output changes section if applicable.

The PR will automatically:
- Request review from `@LerianStudio/devops-team` (via CODEOWNERS)
- Run `pr-validation` and `pr-security-scan` checks
- Apply labels based on which files were changed (via `labeler.yml`)
- Trigger a beta release on merge (`v1.2.3-beta.N`)

### 5. Validate on `develop`

After your PR is merged to `develop`, a beta release is published automatically (e.g., `v1.2.3-beta.1`). Validate your changes by pointing a test caller to the `@develop` ref or the specific beta tag:

```yaml
# In a test caller repository
jobs:
  test:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/your-workflow.yml@develop
    with:
      # ... your inputs
```

Verify that:
- The workflow runs end-to-end without errors
- All existing inputs still work with their default values
- No secrets or tokens are exposed in logs
- No unintended side effects on other workflows

### 6. Promote to `main`

Once validation on `develop` is complete, open a PR from `develop` → `main`.

The PR description should confirm:
- What was tested and where (link to the workflow run)
- That all checks on `develop` passed
- Any breaking changes and their migration path

### 7. Production release (automatic)

After merging to `main`, semantic-release automatically:

1. Analyzes commits since the last release to determine the version bump
2. Creates a new version tag (`v1.2.3`)
3. Generates and commits `CHANGELOG.md`
4. Publishes a GitHub Release with release notes
5. Backmerges `main` → `develop` to keep branches in sync

---

## Testing Workflow Changes

Shared workflows cannot be unit-tested locally. Use the following strategies:

**1. Syntax validation (fast, no push needed)**

```bash
# Install PyYAML if not already available
python3 -m pip install --quiet pyyaml

# Validate YAML syntax of all workflow files
python3 -c "
import yaml, glob, sys
errors = []
for f in glob.glob('.github/workflows/*.yml'):
    try:
        yaml.safe_load(open(f))
        print(f'✅ {f}')
    except yaml.YAMLError as e:
        print(f'❌ {f}: {e}')
        errors.append(f)
sys.exit(len(errors))
"
```

**2. Test on `develop` before promoting**

Pin a test repository to `@develop` or `@vX.Y.Z-beta.N` and trigger a real run. This is the most reliable validation strategy.

**3. Use `workflow_dispatch` for manual testing**

Many workflows support `workflow_dispatch`. Trigger them manually from the Actions tab of the test repository with specific inputs to isolate behavior.

**4. Check for version inconsistencies**

Scan for actions using different versions across workflows — Dependabot will handle updates, but be aware of mixed versions introduced by your PR:

```bash
grep -rh "uses:" .github/workflows/ | sort -u
```

---

## Release Process

```
feature/* ──► develop (beta: v1.2.3-beta.N) ──► main (prod: v1.2.3)
                  ▲                                      │
                  └──────────── backmerge ───────────────┘
```

| Branch | Trigger | Version format | Example |
|---|---|---|---|
| `develop` | PR merge | `v1.2.3-beta.N` | `v1.4.0-beta.2` |
| `main` | PR from `develop` | `v1.2.3` | `v1.4.0` |

Releases are GPG-signed and published as GitHub Releases with the generated `CHANGELOG.md` attached.

**Callers should always pin to a stable tag in production:**

```yaml
# ✅ Recommended — pinned to a stable release
uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-ci.yml@v1.4.0

# ⚠️ Acceptable for testing — always latest beta
uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-ci.yml@develop

# ❌ Avoid in production — no version guarantee
uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-ci.yml@main
```

---

## Repository Structure

```
.
├── .github/
│   ├── CODEOWNERS                  # Auto-assigns reviewers per area
│   ├── ISSUE_TEMPLATE/             # Bug, feature, and docs issue forms
│   ├── labeler.yml                 # Auto-labels PRs by changed files
│   ├── pull_request_template.md    # Structured PR description
│   ├── dependabot.yml              # Weekly action version updates
│   └── workflows/
│       ├── self-release.yml        # This repo's own release pipeline
│       └── *.yml                   # Reusable shared workflows
├── docs/
│   ├── *.md                        # Per-workflow documentation
│   └── plans/                      # Design documents and proposals
├── .releaserc.yml                  # semantic-release configuration
├── CHANGELOG.md                    # Auto-generated — do not edit manually
├── CONTRIBUTING.md                 # This file
├── SECURITY.md                     # Vulnerability reporting policy
└── README.md                       # Workflow index and quick start
```

---

## Important Rules

- **Never** commit directly to `main` or `develop`
- **Always** target `develop` in your PRs (not `main`)
- **Always** use the correct merge strategy — squash for feature PRs, merge commit for releases and backmerges
- **Always** use Conventional Commits — the message type controls the version bump
- **Never** hardcode org-specific values (tokens, org names, URLs) — use `inputs` or `secrets`
- **Always** update `docs/` when you change inputs, outputs, or behavior
- **Ensure** backward compatibility when possible; document breaking changes clearly
- **Validate** end-to-end on `develop` before opening a PR to `main`
- **Report** security issues privately — see [SECURITY.md](SECURITY.md)

---

## Getting Help

- **Questions or ideas?** Open a [GitHub Discussion](https://github.com/LerianStudio/github-actions-shared-workflows/discussions)
- **Found a bug?** Open an [issue](https://github.com/LerianStudio/github-actions-shared-workflows/issues/new/choose) using the Bug Report template
- **Security issue?** Follow the process in [SECURITY.md](SECURITY.md) — do not open a public issue
- **Need urgent help?** Open a [GitHub Discussion](https://github.com/LerianStudio/github-actions-shared-workflows/discussions) or mention `@LerianStudio/devops-team` in your issue/PR
