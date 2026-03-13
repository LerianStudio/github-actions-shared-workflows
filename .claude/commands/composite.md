# Composite Actions — Rules & Conventions

Use these rules whenever creating or editing a composite action in `src/`.

## Before you create anything

**Step 1 — Check if it already exists in this repo**

Search `src/` before starting. If a composite already covers the same capability:

- Summarize what the existing composite does and which inputs it exposes
- Identify the gap between the existing behavior and the new requirement
- Propose an **adaptation plan** (add an input, extend steps, split into two) instead of creating a new file

**Step 2 — Check the GitHub Actions Marketplace first**

Before writing custom steps from scratch, search the [Marketplace](https://github.com/marketplace?type=actions) for an existing action that covers the need:

- Prefer a well-maintained marketplace action over custom shell scripting for non-trivial logic
- Wrap it in a composite if it needs input normalization or additional steps
- Pin to a specific tag or SHA — never `@main` or `@master`
- Document in the composite `README.md` why that action was chosen

Only implement from scratch when no suitable action exists or when existing ones don't meet security or customization requirements.

---

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

## Configurability — defaults first, override when needed

Every composite must be **self-contained with sensible defaults**. A caller should get a safe, useful result with zero extra configuration. Additional inputs allow the workflow (or caller) to override specific behaviors.

**Composite layer — always define defaults:**

```yaml
inputs:
  enable-recommendations:
    description: Include Docker Scout recommendations in the PR comment
    required: false
    default: "true"       # ✅ composite works standalone
  severity-threshold:
    required: false
    default: "high"       # ✅ opinionated but safe default
```

**Rules:**
- All optional inputs must have a `default` — never `required: true` for feature flags
- Never hardcode feature flags — expose them as inputs so they can be overridden by the reusable workflow
- Step-level feature toggles (`if: inputs.enable_xxx`) belong in the **reusable workflow**, not inside the composite

**Three-layer configurability flow:**

```
Caller repo              Reusable workflow           Composite
──────────────────────── ──────────────────────────  ──────────────────────────
enable_docker_scout_     →  enable_docker_scout_    →  enable-recommendations:
recommendations: false      recommendations             ${{ inputs.... }}
                            (passes it down)
```

## Step section titles

When a composite has more than one logical group of steps, separate them with a titled section comment:

```yaml
runs:
  using: composite
  steps:
    # ----------------- Setup -----------------
    - name: Login to Docker Registry
      ...

    # ----------------- Scan -----------------
    - name: Docker Scout CVEs
      ...

    # ----------------- Recommendations -----------------
    - name: Docker Scout Recommendations
      ...
```

**Rules:**
- Format: `# ----------------- Title -----------------` (exact spacing)
- Add when there are 2+ logical groups of steps
- Title must be short and action-oriented
- Place the comment immediately before the first step — no blank line between comment and step

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

## Runner

Composites inherit the runner from the calling job. All usage examples in `README.md` must specify `blacksmith-4vcpu-ubuntu-2404` as the runner:

```yaml
jobs:
  example:
    runs-on: blacksmith-4vcpu-ubuntu-2404   # ✅ required runner
    steps:
      - uses: ./src/config/labels-sync
```

```yaml
# ❌ Never use other runners in examples
runs-on: ubuntu-latest
runs-on: ubuntu-22.04
runs-on: self-hosted
```

## README.md requirements

1. Logo header — HTML table layout (logo left, `h1` title right)
2. Inputs table — `Input | Description | Required | Default`
3. Usage as composite step (full YAML)
4. Usage as reusable workflow (full YAML with `secrets: inherit`)
5. Required permissions block

### Usage example ref policy

Examples in README.md must never use `@main`. Use the correct ref for each context:

```yaml
# ✅ Testing — point to develop or feature branch
uses: LerianStudio/github-actions-shared-workflows/.github/workflows/labels-sync.yml@develop
uses: LerianStudio/github-actions-shared-workflows/.github/workflows/labels-sync.yml@feat/my-branch

# ✅ Production — always a pinned stable version
uses: LerianStudio/github-actions-shared-workflows/.github/workflows/labels-sync.yml@v1.2.3

# ❌ Never in examples
uses: LerianStudio/github-actions-shared-workflows/.github/workflows/labels-sync.yml@main
```

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

## Reserved input names — never use

Never declare composite inputs using GitHub's reserved prefixes — they conflict with runtime variables and break jobs:

```yaml
# ❌ Reserved — conflicts with GitHub's runtime variable
inputs:
  GITHUB_TOKEN:
  GITHUB_SHA:
  ACTIONS_RUNTIME_TOKEN:
  RUNNER_OS:

# ✅ Use kebab-case and distinct names
inputs:
  github-token:
  manage-token:
```

Reserved prefixes: `GITHUB_*`, `ACTIONS_*`, `RUNNER_*`.
