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

## Workflow structure

Every reusable workflow must:
- support `workflow_call` (for external callers)
- support `workflow_dispatch` (for manual testing)
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
  workflow_dispatch:
    inputs:
      environment:
        required: true
        type: string
      dry_run:
        description: Preview changes without applying them
        type: boolean
        default: false
```

## dry_run pattern

The two modes have opposite goals — design them accordingly:

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

## Local path rule (critical)

```yaml
uses: ./src/setup/setup-go      # ✅ composite version matches workflow version
uses: LerianStudio/...@main     # ❌ breaks versioning for callers on older tags
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

## Documentation naming

The doc file in `docs/` must have the **exact same name** as the workflow file, with `.md` extension:

```
.github/workflows/go-ci.yml        → docs/go-ci.md          ✅
.github/workflows/go-ci.yml        → docs/go-ci-workflow.md  ❌
.github/workflows/labels-sync.yml  → docs/labels-sync.md    ✅
```

Every new reusable workflow must have a corresponding `docs/<workflow-name>.md`.

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

# ❌ External ref for composite inside a reusable workflow
uses: LerianStudio/github-actions-shared-workflows/src/setup-go@main

# ❌ Mutable ref on third-party actions
uses: some-action/tool@main
```

## Security rules

- Pin all third-party actions to a specific tag or SHA — Dependabot keeps them updated
- Never use `@main` or `@master` for third-party actions
- Never interpolate untrusted user input directly into `run:` commands
- Never print secrets via `echo`, env dumps, or step summaries
- Complex conditional logic belongs in the workflow, not in composites
