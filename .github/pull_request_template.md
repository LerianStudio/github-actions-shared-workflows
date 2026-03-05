<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>GitHub Actions Shared Workflows</h1></td>
  </tr>
</table>

---

## Description

<!-- Summarize what this PR does and why. Be specific about which workflow(s) are affected and what behavior changes. -->

## Type of Change

<!-- Mark with "x" all that apply -->

- [ ] `feat`: New workflow or new input/output/step in an existing workflow
- [ ] `fix`: Bug fix in a workflow (incorrect behavior, broken step, wrong condition)
- [ ] `perf`: Performance improvement (e.g. caching, parallelism, reduced steps)
- [ ] `refactor`: Internal restructuring with no behavior change
- [ ] `docs`: Documentation only (README, docs/, inline comments)
- [ ] `ci`: Changes to self-CI (workflows under `.github/workflows/` that run on this repo)
- [ ] `chore`: Dependency bumps, config updates, maintenance
- [ ] `test`: Adding or updating tests
- [ ] `BREAKING CHANGE`: Callers must update their configuration after this PR

## Affected Workflows

<!-- Mark all workflows changed by this PR. "Indirect" means the workflow itself didn't change but its behavior may be affected (e.g. a shared step, a config file, a reusable action it depends on). -->

| Category | Changed | Indirect impact |
|---|:---:|:---:|
| Go (ci, security, release, pr-analysis) | | |
| TypeScript (ci, release, frontend-pr-analysis) | | |
| Infrastructure (gitops-update, build, helm-update-chart, dispatch-helm) | | |
| Release & Versioning (release, self-release, gptchangelog) | | |
| Security (go-security, pr-security-scan) | | |
| Utilities (changed-paths, pr-validation, slack-notify, api-dog-e2e-tests) | | |

## What Changed

<!-- Be specific. Describe inputs added/removed/renamed, step logic changes, condition updates, new tools integrated, etc. -->

-
-
-

## Input / Output Changes

<!-- Fill in only if inputs or outputs were added, changed, or removed. Delete this section if not applicable. -->

| Name | Type | Before | After | Required? | Default |
|---|---|---|---|:---:|---|
| | | | | | |

## Breaking Changes

<!-- Required if "BREAKING CHANGE" is checked above. Describe exactly what breaks and provide a migration snippet. -->

> **None.** *(Remove this line and fill in the details if this is a breaking change.)*

<!--
### What breaks

<description of what callers will experience>

### Migration

```yaml
# Before
uses: LerianStudio/github-actions-shared-workflows/.github/workflows/xxx.yml@main
with:
  old_input: value

# After
uses: LerianStudio/github-actions-shared-workflows/.github/workflows/xxx.yml@main
with:
  new_input: value
```
-->

## Testing

<!-- Describe how the changes were validated. Shared workflows can't be unit-tested easily — be explicit about where and how you tested. -->

- [ ] Tested by calling the workflow from a real repository (specify below)
- [ ] Ran the workflow on `develop` ref and verified end-to-end behavior
- [ ] Verified all existing inputs still work with their default values
- [ ] Checked that no secrets or tokens are exposed in logs
- [ ] Reviewed the diff for unintended side effects on other workflows

**Test repository / run link:** <!-- e.g. https://github.com/LerianStudio/some-repo/actions/runs/123 -->

## Checklist

- [ ] PR title follows [Conventional Commits](https://www.conventionalcommits.org/) format (`type(scope): subject`)
- [ ] Commit messages follow Conventional Commits (required for semantic-release)
- [ ] Targeting `develop` branch (not `main` directly)
- [ ] Documentation updated in `docs/` if behavior changed
- [ ] `README.md` updated if a new workflow was added or inputs/outputs changed
- [ ] No hardcoded secrets, tokens, or org-specific values (use inputs or secrets)
- [ ] Backward compatible — or breaking changes are documented above
- [ ] Self-review completed

## Related Issues

Closes #
Related to #
