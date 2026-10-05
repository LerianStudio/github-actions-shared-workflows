#!/usr/bin/env python3
"""Fail when a local workflow call does not honour the callee's secrets contract.

Usage: WORKFLOWS_DIR=.github/workflows python3 check.py

Two rules, both about *declared* contracts:

  1. A call to a workflow that declares at least one secret must forward by
     name. `inherit` hands over every secret the caller repository holds.
  2. An explicit mapping must cover every secret the callee declares. A missing
     one resolves to the empty string at runtime, not to an error.

A callee that declares no secrets is skipped: it depends on inheritance by
construction, and writing contracts for those is a migration, not a lint fix.

The workflow is parsed with yaml.compose() rather than scanned line by line, so
trailing comments, key order, and a job with no `secrets:` key at all are all
handled as YAML rather than as text.
"""
import glob, os, re, sys, yaml

workflows_dir = os.environ.get('WORKFLOWS_DIR', '.github/workflows')
violations = 0

def err(filepath, line, msg):
    global violations
    print(f'::error file={filepath},line={line}::{msg}')
    violations += 1

def declared(name):
    path = os.path.join(workflows_dir, f'{name}.yml')
    if not os.path.isfile(path):
        path = os.path.join(workflows_dir, f'{name}.yaml')
        if not os.path.isfile(path):
            return None
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    trigger = data.get('on', data.get(True))
    if not isinstance(trigger, dict):
        return None
    call = trigger.get('workflow_call')
    if not isinstance(call, dict):
        return None
    return list((call.get('secrets') or {}))

# A local call is spelled relative to the repository root, always under
# .github/workflows/, whatever directory this script was pointed at to read
# the files. Deriving the pattern from workflows_dir coupled the two: an
# absolute --workflows-dir made it match nothing, and the check would skip
# every call instead of failing. Filenames keep their case — `Callee.yml` is a
# valid workflow and must not slip through either.
#
# Two prefixes, both documented: `./` and `$/`. The latter is GitHub's
# recommended form for a same-repository call on github.com (unavailable on
# GitHub Enterprise Server, and it takes no `@ref`). Matching only `./` left
# the recommended spelling unchecked.
LOCAL_RE = re.compile(r'^(?:\./|\$/)\.github/workflows/([^/\\]+)\.ya?ml$')

def entries(node):
    """(key, value_node, key_line) for a YAML mapping node."""
    if not isinstance(node, yaml.MappingNode):
        return []
    return [(k.value, v, k.start_mark.line + 1)
            for k, v in node.value if isinstance(k, yaml.ScalarNode)]

for filepath in sorted(glob.glob(os.path.join(workflows_dir, '*.yml'))):
    with open(filepath) as f:
        try:
            root = yaml.compose(f)
        except Exception as exc:
            err(filepath, 1, f'Could not parse workflow: {exc}')
            continue
    jobs = next((v for k, v, _ in entries(root) if k == 'jobs'), None)
    if jobs is None:
        continue

    for job_name, job, job_line in entries(jobs):
        keys = {k: (v, line) for k, v, line in entries(job)}
        uses = keys.get('uses')
        if not uses or not isinstance(uses[0], yaml.ScalarNode):
            continue
        # The scalar's value excludes any trailing YAML comment.
        match = LOCAL_RE.match(uses[0].value.strip())
        if not match:
            continue
        callee = match.group(1)

        accepts = declared(callee)
        if not accepts:
            # The callee is unreadable, or declares no secrets and therefore
            # depends on inheritance by construction. This check polices
            # declared contracts; it does not invent them.
            continue

        secrets = keys.get('secrets')
        if secrets is None:
            err(filepath, uses[1],
                f'job `{job_name}` calls `{callee}`, which declares '
                f'{", ".join(accepts)}, and forwards nothing. An unforwarded '
                f'secret resolves to an empty string: the job runs and the '
                f'feature it guards silently does nothing.')
            continue

        node, line = secrets
        if isinstance(node, yaml.ScalarNode):
            if node.value.strip() == 'inherit':
                err(filepath, line,
                    f'job `{job_name}` calls `{callee}`, which declares a secrets '
                    f'contract ({", ".join(accepts)}), so it must be forwarded by '
                    f'name — `inherit` hands it every secret the caller repository '
                    f'holds.')
            continue

        passed = {k for k, _, _ in entries(node)}
        missing = [s for s in accepts if s not in passed]
        if missing:
            err(filepath, line,
                f'job `{job_name}` calls `{callee}`, which declares '
                f'{", ".join(missing)}, and this call does not forward '
                f'{"them" if len(missing) > 1 else "it"}. An unforwarded secret '
                f'resolves to an empty string: the job runs and the feature it '
                f'guards silently does nothing.')

if violations > 0:
    print(f'::error::Found {violations} workflow secrets contract violation(s).')
    sys.exit(1)

print('Every local workflow call forwards the full secrets contract of the workflow it calls.')
