<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>pinned-actions</h1></td>
  </tr>
</table>

Enforces the repository pinning policy on every `uses:` reference in workflow and composite files. External actions must be pinned by commit SHA; internal (`LerianStudio/`) references are validated against the composite-vs-reusable policy below.

## Policy

| Ref kind | Detection | Required pin | Severity on violation |
|---|---|---|---|
| **External action** (anything outside the org) | `uses:` path does not match any `warn-patterns` prefix | Full commit SHA (40–64 hex chars) | ❌ **error** — fails the step |
| **Internal composite** | `uses:` path contains `/src/` | Floating major tag (`@v1`, `@v2`, …) or testing branch (`@develop` / `@main`) | ⚠️ **warning** |
| **Internal reusable workflow** | `uses:` path contains `/.github/workflows/` | Exact version tag (`@v1.2.3`, `@v1.2.3-beta.1`) or testing branch (`@develop` / `@main`) | ⚠️ **warning** |
| **Internal, unknown shape** | matches `warn-patterns` but neither path pattern above | Any semver-like tag or testing branch (legacy tolerance) | ⚠️ **warning** |

**Rationale**

- Composites are small, low-risk building blocks. Floating `@v1` lets callers track the latest stable major without bumping per patch — the repo release pipeline moves `@v1` atomically on each stable release in `main`.
- Reusable workflows orchestrate entire pipelines with broader blast radius. Exact pinning (`@v1.2.3`) forces explicit, auditable caller updates.
- External actions use SHA pins because upstream tags are mutable — Dependabot keeps the SHAs fresh automatically.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `files` | Comma-separated list of workflow/composite files to check (empty = skip) | No | `""` |
| `warn-patterns` | Pipe-separated org/owner prefixes treated as internal (warn-only) | No | `LerianStudio/` |

## Usage

```yaml
- name: Pinned Actions Check
  uses: LerianStudio/github-actions-shared-workflows/src/lint/pinned-actions@v1
  with:
    files: ".github/workflows/ci.yml,.github/workflows/deploy.yml"
```

## Examples

```yaml
# ✅ External action — SHA pin (required)
uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6

# ❌ External action — tag pin (error)
uses: actions/checkout@v6

# ✅ Internal composite — floating major
uses: LerianStudio/github-actions-shared-workflows/src/security/trivy-fs-scan@v1

# ⚠️ Internal composite — exact version (warning, should be @v1)
uses: LerianStudio/github-actions-shared-workflows/src/security/trivy-fs-scan@v1.24.1

# ✅ Internal reusable workflow — exact version
uses: LerianStudio/github-actions-shared-workflows/.github/workflows/release.yml@v1.26.0

# ⚠️ Internal reusable workflow — floating major (warning, should be @vX.Y.Z)
uses: LerianStudio/github-actions-shared-workflows/.github/workflows/release.yml@v1

# ✅ Either kind — develop/main for testing a change
uses: LerianStudio/github-actions-shared-workflows/src/config/labels-sync@develop
```

## Required permissions

```yaml
permissions:
  contents: read
```
