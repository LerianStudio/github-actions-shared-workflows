package main

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// The fixtures live in the test rather than as .yaml files so the repository's
// yamllint pass never trips over the deliberately broken one.
const (
	validManifest = `service: example
version: 1
roles:
  - name: viewer
  - name: editor
permissions:
  - { resource: accounts, action: get, effect: allow, roles: [viewer, editor] }
  - { resource: accounts, action: patch, effect: allow, roles: [editor] }
`

	// The schema-drift shape that reached the catalog before this check existed
	// (reporter, br-ccs): no version and permissions granted to undeclared roles.
	oldSchemaManifest = `service: reporter
permissions:
  - resource: templates
    actions: [get, post]
    roles: [reporter-viewer]
`

	badYAML = "service: broken\npermissions: [\n"
)

func writeManifest(t *testing.T, name, body string) string {
	t.Helper()

	path := filepath.Join(t.TempDir(), name)
	if err := os.WriteFile(path, []byte(body), 0o600); err != nil {
		t.Fatal(err)
	}

	return path
}

func TestValidManifest(t *testing.T) {
	service, err := validateManifest([]byte(validManifest))
	if err != nil {
		t.Fatalf("expected valid manifest, got %v", err)
	}

	if service != "example" {
		t.Fatalf("service = %q, want example", service)
	}
}

func TestOldSchemaManifestIsRejected(t *testing.T) {
	_, err := validateManifest([]byte(oldSchemaManifest))
	if err == nil {
		t.Fatal("expected the old-schema manifest to be rejected")
	}

	for _, want := range []string{
		"version must be a positive integer",
		`references undeclared role "reporter-viewer"`,
	} {
		if !strings.Contains(err.Error(), want) {
			t.Errorf("error %q does not mention %q", err, want)
		}
	}
}

func TestBadYAMLIsRejected(t *testing.T) {
	if _, err := validateManifest([]byte(badYAML)); err == nil || !strings.Contains(err.Error(), "parse yaml manifest") {
		t.Fatalf("expected a yaml parse error, got %v", err)
	}
}

func TestEmptyManifestIsRejected(t *testing.T) {
	if _, err := validateManifest(nil); err == nil || !strings.Contains(err.Error(), "service must not be empty") {
		t.Fatalf("expected an empty-service error, got %v", err)
	}
}

func TestRunReportsEveryManifest(t *testing.T) {
	var out bytes.Buffer

	valid := writeManifest(t, "valid.yaml", validManifest)

	code := run([]string{
		valid,
		writeManifest(t, "old.yaml", oldSchemaManifest),
		writeManifest(t, "bad.yaml", badYAML),
		filepath.Join(t.TempDir(), "missing.yaml"),
	}, &out)

	if code != 1 {
		t.Fatalf("exit code = %d, want 1", code)
	}

	got := out.String()
	if strings.Count(got, "::error ") != 3 {
		t.Fatalf("expected 3 error annotations, got:\n%s", got)
	}

	if !strings.Contains(got, "valid: "+valid) {
		t.Fatalf("valid manifest not reported:\n%s", got)
	}

	if !strings.Contains(got, "3 of 4 permission manifest(s) invalid") {
		t.Fatalf("summary line missing:\n%s", got)
	}
}

func TestRunAllValid(t *testing.T) {
	var out bytes.Buffer

	if code := run([]string{writeManifest(t, "valid.yaml", validManifest)}, &out); code != 0 {
		t.Fatalf("exit code = %d, want 0:\n%s", code, out.String())
	}
}

func TestRunWithoutArgs(t *testing.T) {
	var out bytes.Buffer

	if code := run(nil, &out); code != 2 {
		t.Fatalf("exit code = %d, want 2", code)
	}
}

func TestAnnotationEscaping(t *testing.T) {
	if got := escapeData("a\nb%c\r"); got != "a%0Ab%25c%0D" {
		t.Fatalf("escapeData = %q", got)
	}

	if got := escapeProperty("a,b:c"); got != "a%2Cb%3Ac" {
		t.Fatalf("escapeProperty = %q", got)
	}
}
