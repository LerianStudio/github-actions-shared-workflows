<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>docker-build-ts</h1></td>
  </tr>
</table>

Composite action that builds and pushes a Docker image for a single TypeScript/Node.js component. Automatically injects an `npmrc` secret for GitHub Packages `@lerianstudio` private dependencies.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `enable-dockerhub` | Enable pushing to DockerHub | No | `false` |
| `enable-ghcr` | Enable pushing to GHCR | No | `true` |
| `dockerhub-org` | DockerHub organization name | No | `lerianstudio` |
| `ghcr-org` | GHCR organization name (defaults to repo owner) | No | `""` |
| `dockerhub-username` | DockerHub username | If DockerHub enabled | `""` |
| `dockerhub-password` | DockerHub password | If DockerHub enabled | `""` |
| `ghcr-token` | Token for GHCR login and npmrc authentication | Yes | — |
| `app-name` | Image name for this component | Yes | — |
| `working-dir` | Working directory for this component | No | `.` |
| `dockerfile` | Dockerfile path relative to working-dir | No | `""` |
| `dockerfile-name` | Default Dockerfile name when `dockerfile` is not set | No | `Dockerfile` |
| `build-context` | Docker build context | No | `.` |
| `build-secrets` | Additional secrets (one per line). npmrc is always included. | No | `""` |
| `platforms` | Target platforms | No | `linux/amd64` |
| `version` | Semver version from tag (e.g., `v1.0.0-beta.1`) | Yes | — |
| `is-release` | Whether this is a production release | No | `false` |
| `dry-run` | Build without pushing | No | `false` |

## Outputs

| Output | Description |
|--------|-------------|
| `image-digest` | Digest of the pushed image |
| `image-tags` | Tags applied to the image |

## Usage as composite step

```yaml
steps:
  - name: Checkout
    uses: actions/checkout@v4

  - name: Build and push
    uses: ./src/build/docker-build-ts
    with:
      ghcr-token: ${{ secrets.MANAGE_TOKEN }}
      app-name: my-app
      version: v1.0.0-beta.1
      platforms: linux/amd64
```

## Usage via reusable workflow

```yaml
jobs:
  build:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/typescript-build.yml@v1.0.0
    with:
      components_json: '[{"name":"my-app","working_dir":".","dockerfile":"Dockerfile"}]'
    secrets: inherit
```

## Required permissions

```yaml
permissions:
  contents: read
  packages: write
```

## Dockerfile requirements

Dockerfiles must mount the `npmrc` secret for installing private packages:

```dockerfile
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc npm install
```
