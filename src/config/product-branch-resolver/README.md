<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>product-branch-resolver</h1></td>
  </tr>
</table>

Resolves which product a branch belongs to, for repositories where each product owns a long-lived branch. `develop-midaz` resolves to `midaz`, `develop-tracer` to `tracer`, and anything that does not match the pattern resolves to nothing.

It only reads the branch name — no git history, no API calls, no side effects. Callers use it to decide whether a ref represents a product and, when it does, what to name the artifact built from it.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `ref-name` | Branch name being built (e.g. `github.ref_name`) | Yes | |
| `branch-pattern` | Branch pattern with **exactly one** `*`. The text replacing it becomes the product name. | No | `develop-*` |
| `excluded-products` | Comma-separated product names that must not be treated as a product, even when the branch matches | No | `''` |

## Outputs

| Output | Description |
|--------|-------------|
| `has-product` | `'true'` when `ref-name` matches `branch-pattern` and the product is not excluded |
| `product` | Product name extracted from the branch, empty when `has-product` is `'false'` |

The action fails the run when the extracted product name does not match `^[a-z0-9][a-z0-9-]*$` — the name reaches an image tag, so it is held to a conservative charset rather than trusted from the branch.

### One wildcard, not zero and not several

`branch-pattern` takes **exactly one** `*`. It is not a full glob: the name is split into the text before the placeholder and the text after it, so a second `*` would survive as a literal character in the suffix and the pattern would quietly stop matching anything.

| Pattern | Result |
|---|---|
| `develop-*` | accepted — `develop-midaz` → `midaz` |
| `alpha/*` | accepted — `alpha/midaz` → `midaz` |
| `develop` | rejected — no placeholder |
| `develop-*-preview-*` | rejected — two placeholders |

A pattern with more than one placeholder has no single-wildcard equivalent; a branch layout that needs it wants a different resolver, not this one. Earlier revisions accepted such a pattern and silently matched nothing, so the failure is now explicit.

## Usage as composite step

```yaml
jobs:
  example:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    steps:
      - name: Resolve product from branch
        id: resolve
        uses: LerianStudio/github-actions-shared-workflows/src/config/product-branch-resolver@v1.x.x
        with:
          ref-name: ${{ github.ref_name }}
          excluded-products: core

      - name: Build something for this product
        if: steps.resolve.outputs.has-product == 'true'
        run: echo "building for ${{ steps.resolve.outputs.product }}"
```

## Usage as reusable workflow

Consumed by [`js-alpha-preview.yml`](../../../docs/js-alpha-preview.md), which builds a disposable preview image per product branch:

```yaml
jobs:
  preview:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/js-alpha-preview.yml@v1.x.x
    with:
      excluded_products: core
    secrets: inherit
```

## Required permissions

```yaml
permissions:
  contents: read
```
