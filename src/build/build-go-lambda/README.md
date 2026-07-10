<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>build-go-lambda</h1></td>
  </tr>
</table>

Composite action that compiles a Go AWS Lambda into a `bootstrap` binary for the
`provided.al2*` custom runtime and packages it as a deployable zip artifact.
Defaults target `linux/arm64` with symbols stripped and the `lambda.norpc` build
tag for a smaller runtime footprint. Requires the repository to be checked out
first.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `go-version` | Go version to install (passed to `actions/setup-go`) | No | `1.23` |
| `main-package` | Path to the Go main package to build (e.g. `./cmd/authorizer`) | No | `.` |
| `goos` | Target operating system | No | `linux` |
| `goarch` | Target architecture (`arm64` or `amd64`) | No | `arm64` |
| `build-tags` | Comma-separated Go build tags | No | `lambda.norpc` |
| `ldflags` | Linker flags passed to `go build` | No | `-s -w` |
| `cgo-enabled` | Value for `CGO_ENABLED` | No | `0` |
| `artifact-name` | File name of the generated zip artifact | No | `bootstrap.zip` |
| `working-directory` | Directory to run the build from (must contain `go.mod`) | No | `.` |

## Outputs

| Output | Description |
|--------|-------------|
| `artifact-path` | Path to the generated zip artifact, relative to the workspace |
| `artifact-name` | File name of the generated zip artifact |
| `binary-sha256` | SHA-256 checksum of the built `bootstrap` binary |

## Usage as composite step

```yaml
steps:
  - name: Checkout
    uses: actions/checkout@v4

  - name: Build Go Lambda
    id: build
    uses: LerianStudio/github-actions-shared-workflows/src/build/build-go-lambda@v1
    with:
      main-package: ./cmd/authorizer
      goarch: arm64
      artifact-name: authorizer.zip
```

## Usage via reusable workflow

```yaml
jobs:
  release:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-lambda-release.yml@v1
    with:
      main_package: ./cmd/authorizer
      artifact_name: authorizer.zip
      s3_bucket: my-artifacts-bucket
      s3_key_prefix: casdoor-authorizer
    secrets: inherit
```

## Required permissions

The composite only builds and packages, so no special permissions are required
for the build step itself:

```yaml
permissions:
  contents: read
```

Uploading the artifact (handled by the `go-lambda-release` reusable workflow)
additionally requires `id-token: write` for AWS OIDC.
