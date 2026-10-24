// Command validator checks permission manifests (permissions.yaml) before the
// permission-manifest-publish composite uploads them to the RI catalog.
//
// It applies exactly the check the tenant-manager applies when it loads the
// catalog (components/tenant-manager/internal/adapters/s3/permission_catalog_loader.go,
// parseManifest): yaml.Unmarshal into lib-auth's declaration.DeclarationManifest,
// then DeclarationManifest.Validate(). A manifest that passes here is one the
// tenant-manager will accept; one that fails here is one it would reject, so it
// must never reach the bucket.
//
// The module pins its own lib-auth version and never reads the caller's go.mod,
// so it works the same in a Go service, a monorepo or a repo with no Go at all.
//
// Usage: validator <manifest> [<manifest>...]
//
// Every manifest is checked (no early exit) so one run reports every problem.
// Exit codes: 0 all valid, 1 at least one invalid, 2 usage error.
package main

import (
	"fmt"
	"io"
	"os"
	"strings"

	"github.com/LerianStudio/lib-auth/v5/auth/declaration"
	"gopkg.in/yaml.v3"
)

// validateManifest mirrors the tenant-manager's parseManifest. It returns the
// declared service (possibly empty) and the parse or validation error.
func validateManifest(raw []byte) (string, error) {
	var manifest declaration.DeclarationManifest

	if err := yaml.Unmarshal(raw, &manifest); err != nil {
		return "", fmt.Errorf("parse yaml manifest: %w", err)
	}

	if err := manifest.Validate(); err != nil {
		return manifest.Service, fmt.Errorf("validate manifest %q: %w", manifest.Service, err)
	}

	return manifest.Service, nil
}

// escapeData escapes a workflow-command message so a multi-line or %-bearing
// error cannot break (or forge) the annotation.
func escapeData(s string) string {
	return strings.NewReplacer("%", "%25", "\r", "%0D", "\n", "%0A").Replace(s)
}

// escapeProperty escapes a workflow-command property value (file=...).
func escapeProperty(s string) string {
	return strings.NewReplacer("%", "%25", "\r", "%0D", "\n", "%0A", ":", "%3A", ",", "%2C").Replace(s)
}

func run(paths []string, stdout io.Writer) int {
	if len(paths) == 0 {
		_, _ = fmt.Fprintln(stdout, "::error title=Permission manifest validation::usage: validator <manifest> [<manifest>...]")
		return 2
	}

	invalid := 0

	for _, path := range paths {
		raw, err := os.ReadFile(path)
		if err == nil {
			var service string

			service, err = validateManifest(raw)
			if err == nil {
				_, _ = fmt.Fprintf(stdout, "valid: %s (service %q)\n", path, service)
				continue
			}
		}

		invalid++

		_, _ = fmt.Fprintf(stdout, "::error file=%s,title=Invalid permission manifest::%s\n",
			escapeProperty(path), escapeData(fmt.Sprintf("%s: %v", path, err)))
	}

	if invalid > 0 {
		_, _ = fmt.Fprintf(stdout, "%d of %d permission manifest(s) invalid\n", invalid, len(paths))
		return 1
	}

	_, _ = fmt.Fprintf(stdout, "%d permission manifest(s) valid\n", len(paths))

	return 0
}

func main() {
	os.Exit(run(os.Args[1:], os.Stdout))
}
