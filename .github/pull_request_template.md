<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td><img src="https://github.com/LerianStudio.png" width="72" alt="Lerian" /></td>
    <td><h1>GitHub Actions Shared Workflows</h1></td>
  </tr>
</table>

---

## Description

<!-- Summarize what this PR does and why. List which workflow(s) are affected and what behavior changes. -->

## Type of Change

- [ ] `feat`: New workflow or new input/output/step in an existing workflow
- [ ] `fix`: Bug fix in a workflow (incorrect behavior, broken step, wrong condition)
- [ ] `perf`: Performance improvement (e.g. caching, parallelism, reduced steps)
- [ ] `refactor`: Internal restructuring with no behavior change
- [ ] `docs`: Documentation only (README, docs/, inline comments)
- [ ] `ci`: Changes to self-CI (workflows under `.github/workflows/` that run on this repo)
- [ ] `chore`: Dependency bumps, config updates, maintenance
- [ ] `test`: Adding or updating tests
- [ ] `BREAKING CHANGE`: Callers must update their configuration after this PR

## Breaking Changes

<!-- If applicable, describe exactly what breaks and how callers should migrate. Remove this section if not applicable. -->

None.

## Testing

<!-- Shared workflows can't be unit-tested locally. Describe how you validated the change. -->

- [ ] YAML syntax validated locally
- [ ] Triggered a real workflow run on a caller repository using `@develop` or the beta tag
- [ ] Verified all existing inputs still work with default values
- [ ] Confirmed no secrets or tokens are printed in logs
- [ ] Checked that unrelated workflows are not affected

**Caller repo / workflow run:** <!-- Link to the Actions run that validated this change -->

## Related Issues

Closes #
