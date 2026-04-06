<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>cosign-sign</h1></td>
  </tr>
</table>

Composite action that signs container images using [Sigstore cosign](https://github.com/sigstore/cosign) with keyless (OIDC) signing. Uses the GitHub Actions OIDC identity provider — no private keys to manage. Signatures are stored in the registry alongside the image.

## Inputs

| Input | Description | Required | Default |
|---|---|:---:|---|
| `image-refs` | Newline-separated fully qualified image references to sign (e.g., `docker.io/org/app@sha256:abc...`) | Yes | — |
| `cosign-version` | Cosign version to install | No | `v2.5.0` |
| `dry-run` | Log what would be signed without actually signing | No | `false` |

## Outputs

| Output | Description |
|---|---|
| `signed-refs` | Newline-separated list of successfully signed image references |

## Usage

### As a composite step (after Docker build and push)

```yaml
jobs:
  build:
    runs-on: blacksmith-4vcpu-ubuntu-2404
    permissions:
      contents: read
      packages: write
      id-token: write   # required for keyless signing
    steps:
      - uses: actions/checkout@v6

      - name: Build and push Docker image
        id: build-push
        uses: docker/build-push-action@v7
        with:
          push: true
          tags: myorg/myapp:1.0.0

      - name: Sign container image
        uses: LerianStudio/github-actions-shared-workflows/src/security/cosign-sign@v1.x.x
        with:
          image-refs: docker.io/myorg/myapp@${{ steps.build-push.outputs.digest }}
```

### Signing multiple registries

```yaml
      - name: Sign container images
        uses: LerianStudio/github-actions-shared-workflows/src/security/cosign-sign@v1.x.x
        with:
          image-refs: |
            docker.io/myorg/myapp@${{ steps.build-push.outputs.digest }}
            ghcr.io/myorg/myapp@${{ steps.build-push.outputs.digest }}
```

### Verifying signatures

```bash
cosign verify \
  --certificate-identity-regexp="^https://github\.com/LerianStudio/.+/.github/workflows/.+@refs/(heads|tags)/.+$" \
  --certificate-oidc-issuer="https://token.actions.githubusercontent.com" \
  docker.io/myorg/myapp@sha256:abc123...
```

## Permissions required

```yaml
permissions:
  id-token: write   # required — OIDC token for keyless signing
  packages: write   # if pushing signatures to GHCR
```

> **Note:** The calling job must have `id-token: write` permission for keyless signing to work. Without it, cosign cannot obtain an OIDC token and the signing step will fail.
