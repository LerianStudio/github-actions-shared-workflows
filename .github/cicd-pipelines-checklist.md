
CI/CD Pipeline Configuration Checklist
This checklist documents all changes needed to standardize CI/CD pipelines using LerianStudio shared workflows.

Prerequisites
Ensure develop and release-candidate branches exist in the repository
Create feature branch: git checkout -b feature/apply_pipeline
1. GitHub Workflows
1.1 Go Combined Analysis (go-combined-analysis.yml)
Create/update .github/workflows/go-combined-analysis.yml
Configure triggers for pull_request on develop, release-candidate, main
Add paths-ignore for non-code files:
paths-ignore:
  - '**.md'
  - 'docs/**'
  - '.github/**'
  - 'LICENSE'
  - 'CODEOWNERS'
  - '.gitignore'
  - '.editorconfig'
  - '*.png'
  - '*.jpg'
  - '*.svg'

Use shared workflow: LerianStudio/github-actions-shared-workflows/.github/workflows/go-pr-analysis.yml@v1.3.3
Set runner_type: "blacksmith-4vcpu-ubuntu-2404"
Configure filter_paths for monorepo (JSON array) or leave empty for single-app
Set path_level: 2 for monorepo
Set app_name_prefix (e.g., “midaz”, “fetcher”)
Set go_version: "1.25" (or project’s Go version)
Set golangci_lint_version: "v2.6.2" (or latest)
Set coverage_threshold: 85
Set fail_on_coverage_threshold: true (or false for initial setup)
Add go_private_modules: "github.com/LerianStudio/*" if using private modules
Use secrets: inherit
1.2 PR Validation (pr-validation.yml)
Create/update .github/workflows/pr-validation.yml
Configure triggers for pull_request on develop, release-candidate, main
Do NOT add paths-ignore (validation should run on all PRs)
Use shared workflow: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-validation.yml@v1.3.3
Set runner_type: "blacksmith-4vcpu-ubuntu-2404"
Configure pr_title_types (conventional commit types)
Configure pr_title_scopes (optional, project-specific)
Set require_scope: false
Set min_description_length: 50
Set check_changelog: true
Set enable_auto_labeler: true
Set labeler_config_path: '.github/labeler.yml'
Use secrets: inherit
1.3 PR Security Scan (pr-security-scan.yml)
Create/update .github/workflows/pr-security-scan.yml
Configure triggers for pull_request on develop, release-candidate, main
Add paths-ignore (same as go-combined-analysis)
Use shared workflow: LerianStudio/github-actions-shared-workflows/.github/workflows/pr-security-scan.yml@v1.3.3
Set runner_type: "blacksmith-4vcpu-ubuntu-2404"
Configure filter_paths for monorepo (newline-separated) or leave empty
Set path_level: "2" for monorepo
Set dockerhub_org: "lerianstudio"
Use secrets: inherit
1.4 Build (build.yml)
Create/update .github/workflows/build.yml
Configure trigger for push on tags: ['**']
Do NOT add paths-ignore (runs on tags only)
Use shared workflow: LerianStudio/github-actions-shared-workflows/.github/workflows/build.yml@v1.3.3
Set runner_type: "blacksmith-4vcpu-ubuntu-2404"
Configure filter_paths for monorepo (newline-separated)
Set path_level: 2 for monorepo
Set app_name_prefix (e.g., “midaz”, “fetcher”)
Set enable_dockerhub: true
Set enable_ghcr: true
Set dockerhub_org: lerianstudio
Set enable_gitops_artifacts: true (if using GitOps)
Use secrets: inherit
1.4.1 GitOps Update Job (if applicable)
Add update_gitops job after build
Use shared workflow: LerianStudio/github-actions-shared-workflows/.github/workflows/gitops-update.yml@v1.3.3
Set runner_type: "blacksmith-4vcpu-ubuntu-2404"
Configure gitops_repository, gitops_server, app_name
Configure yaml_key_mappings for each component
Set enable_argocd_sync: true and argocd_app_name
Use secrets: inherit
1.4.2 E2E Tests Job (if applicable)
Add api-dog-e2e-tests job after GitOps update
Use shared workflow: LerianStudio/github-actions-shared-workflows/.github/workflows/api-dog-e2e-tests.yml@v1.3.3
Set runner_type: "firmino-lxc-runners" (must use firmino for E2E)
Set auto_detect_environment: true
Pass secrets explicitly (not inherit):
test_scenario_id
apidog_access_token
dev_environment_id
stg_environment_id
1.5 Release (release.yml)
Create/update .github/workflows/release.yml
Configure trigger for push on branches: [develop, release-candidate, main]
Do NOT add paths-ignore (semantic-release handles filtering)
Use shared workflow: LerianStudio/github-actions-shared-workflows/.github/workflows/release.yml@v1.3.3
Set runner_type: "blacksmith-4vcpu-ubuntu-2404"
Configure filter_paths for monorepo (if applicable)
Use secrets: inherit
2. Configuration Files
2.1 Labeler (labeler.yml)
Create .github/labeler.yml
Configure labels based on file paths:
documentation for docs, README, etc.
ci for workflow files
dependencies for go.mod, go.sum
Component-specific labels for monorepo
2.2 Semantic Release (.releaserc.yml)
Create .releaserc.yml at repository root
Configure branches: develop (beta), release-candidate (rc), main (release)
Configure plugins: commit-analyzer, release-notes-generator, changelog, github, git
Set tagFormat: "v${version}"
2.3 GolangCI-Lint (.golangci.yml)
Create .golangci.yml at repository root
Configure linters (match organization standards)
Set appropriate timeouts
Configure exclusions for generated code
2.4 Dependabot (dependabot.yml)
Create .github/dependabot.yml
Configure for gomod package ecosystem
Set update schedule (e.g., weekly)
Set target branch: develop
For monorepo: add separate entries per component directory
2.5 CODEOWNERS
Create .github/CODEOWNERS
Define ownership for repository root
For monorepo: define per-component ownership
Include CI/CD files ownership
3. Repository Files
3.1 Dockerfile
Ensure each component has a Dockerfile
Update app name references (not boilerplate)
Follow multi-stage build pattern
3.2 Issue Templates
Create .github/ISSUE_TEMPLATE/BUG-REPORT.yaml
Create .github/ISSUE_TEMPLATE/FEATURE-REQUEST.yaml
Create .github/ISSUE_TEMPLATE/config.yaml (with contact links)
3.3 Security
Create SECURITY.md with vulnerability reporting instructions
Include GitHub Security Advisory as preferred method
Include email fallback
3.4 Funding
Create .github/FUNDING.yml (if applicable)
4. Runner Configuration
4.1 Standard Jobs
Use blacksmith-4vcpu-ubuntu-2404 for:
Go analysis (lint, tests, coverage, build)
PR validation
PR security scan
Docker build
Release
GitOps update
4.2 E2E Tests
Use firmino-lxc-runners for:
API Dog E2E tests (requires access to firmino environment)
5. Secrets Configuration
5.1 Organization Secrets (inherited via secrets: inherit)
DOCKER_USERNAME
DOCKER_PASSWORD
MANAGE_TOKEN
SLACK_WEBHOOK_URL
APIDOG_ACCESS_TOKEN
LERIAN_CI_CD_USER_NAME
LERIAN_CI_CD_USER_EMAIL
5.2 Repository-Specific Secrets
{APP}_APIDOG_TEST_SCENARIO_ID
{APP}_APIDOG_DEV_ENVIRONMENT_ID
{APP}_APIDOG_STG_ENVIRONMENT_ID
6. Monorepo-Specific Configuration
6.1 filter_paths Format
go-combined-analysis.yml: JSON array '["components/a", "components/b"]'
pr-security-scan.yml: Newline-separated (YAML block scalar)
build.yml: Newline-separated (YAML block scalar)
6.2 path_level
Set to 2 for components/{name} structure
Adjust based on your directory depth
6.3 Component Updates
When adding new components, update all workflow filter_paths
Update yaml_key_mappings in GitOps job
Update dependabot.yml with new component directory
Update CODEOWNERS with new component ownership
7. Cleanup
Remove any // trigger or // trigger pipeline comments from code
Move legacy/deprecated workflows to backup folder (e.g., {app}-bkp-pipelines/)
Remove unused workflow files
8. Verification
Push feature branch
Create PR targeting develop
Verify all workflows trigger correctly:
Go Combined Analysis runs
PR Validation runs
PR Security Scan runs
Check for merge conflicts
Verify coverage reports appear as PR comments
Verify Slack notifications work (on merge)
Quick Reference: Shared Workflow Versions
Workflow	Version
go-pr-analysis.yml	v1.3.3
pr-validation.yml	v1.3.3
pr-security-scan.yml	v1.3.3
build.yml	v1.3.3
release.yml	v1.3.3
gitops-update.yml	v1.3.3
api-dog-e2e-tests.yml	v1.3.3
Example: Single-App Workflow Reference
# go-combined-analysis.yml (single app)
jobs:
  go-analysis:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-pr-analysis.yml@v1.3.3
    with:
      runner_type: "blacksmith-4vcpu-ubuntu-2404"
      app_name_prefix: "myapp"
      go_version: "1.25"
      coverage_threshold: 85
      fail_on_coverage_threshold: true
    secrets: inherit

Example: Monorepo Workflow Reference
# go-combined-analysis.yml (monorepo)
jobs:
  go-analysis:
    uses: LerianStudio/github-actions-shared-workflows/.github/workflows/go-pr-analysis.yml@v1.3.3
    with:
      runner_type: "blacksmith-4vcpu-ubuntu-2404"
      filter_paths: '["components/api", "components/worker"]'
      path_level: 2
      app_name_prefix: "myapp"
      go_version: "1.25"
      coverage_threshold: 85
      fail_on_coverage_threshold: true
    secrets: inherit

