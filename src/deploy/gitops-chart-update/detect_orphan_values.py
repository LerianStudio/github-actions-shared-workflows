#!/usr/bin/env python3
"""Flag a key set in an environment that no longer exists in the chart.

The safety net that depends on nobody remembering anything. The charts'
values.schema.json is permissive — midaz has 106 `additionalProperties: true`
against 2 `false` — so `helm template` happily accepts a key the chart no longer
knows and the deploy comes up on the default. This check needs neither the schema
nor any repair step ahead of it.

It compares the leaf keys of the environment values.yaml against those of the
chart values.yaml. Keys present in the environment and absent from the chart are
reported.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

# Free-form subtrees: the chart does not declare the keys inside them, so a
# leaf-by-leaf comparison there would only produce false positives.
FREE_FORM = {
    "extraEnv",
    "extraEnvVars",
    "podAnnotations",
    "annotations",
    "labels",
    "podLabels",
    "nodeSelector",
    "configmap",
    "secrets",
    "env",
}


def leaves(node, prefix: str = "") -> set[str]:
    found = set()
    if not isinstance(node, dict):
        return {prefix} if prefix else set()
    for key, value in node.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if key in FREE_FORM:
            found.add(path)
            continue
        if isinstance(value, dict) and value:
            found |= leaves(value, path)
        else:
            found.add(path)
    return found


def load(path: Path):
    with path.open() as handle:
        return yaml.safe_load(handle) or {}


def open_paths(node, prefix: str = "") -> set[str]:
    """Paths the chart declares as an open extension point.

    An empty map means "fill this in" — the Lerian mask pattern, where a chart
    declares `global: {datastores: {}}` and the environment supplies the
    contents. A free-form subtree is the same promise by name.

    Kept apart from the leaf set on purpose. A scalar leaf and an empty map are
    indistinguishable once flattened, and treating both as extensible would
    accept `image.tag` against a chart whose `image` is the string `nginx` —
    a subtree the chart cannot read, which is exactly what this check is for.
    """
    found = set()
    if not isinstance(node, dict):
        return found
    for key, value in node.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        # A scalar is never an extension point, whatever it is called. This
        # chart really does ship `boilerplate.env: production` — a plain string
        # under a name that appears in FREE_FORM — and nothing can be nested
        # inside it, so `boilerplate.env.FOO` has to stay an orphan.
        if not isinstance(value, dict):
            continue
        if key in FREE_FORM:
            # Declared free-form: the chart never names what goes inside, so
            # the whole subtree is open whether or not it ships defaults.
            found.add(path)
            continue
        if value:
            found |= open_paths(value, path)
        else:
            found.add(path)
    return found


def ancestors(key: str) -> set[str]:
    """Every proper ancestor path of a dotted key.

    "global.datastores.postgres.host" gives {"global", "global.datastores",
    "global.datastores.postgres"}.
    """
    parts = key.split(".")
    return {".".join(parts[:index]) for index in range(1, len(parts))}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chart-values", required=True, type=Path)
    parser.add_argument("--env-values", required=True, type=Path, nargs="+")
    parser.add_argument(
        "--fail-on-orphan",
        action="store_true",
        help="Exit non-zero when an orphan is found. Otherwise only report.",
    )
    args = parser.parse_args()

    chart_values = load(args.chart_values)
    chart_keys = leaves(chart_values)
    chart_open = open_paths(chart_values)

    report, orphan_total = [], 0
    for env_path in args.env_values:
        if not env_path.is_file():
            continue
        # An environment key is accepted when the chart names it exactly, or
        # when it sits under a path the chart left open. The second case is what
        # makes the Lerian mask pattern work: a chart declares
        # `global: {datastores: {}}` and the environment fills it in, so
        # global.datastores.postgres.host is legitimate even though the chart
        # never names it.
        #
        # Only open paths grant that, never any leaf: `image: nginx` must not
        # absorb `image.tag`, which the chart cannot read.
        orphans = sorted(
            key
            for key in leaves(load(env_path))
            if key not in chart_keys and not (ancestors(key) & chart_open)
        )
        orphan_total += len(orphans)
        report.append({"file": str(env_path), "orphans": orphans})
        for orphan in orphans:
            print(
                f"::warning file={env_path}::`{orphan}` does not exist in the new chart. "
                "The chart will ignore it silently and use its own default.",
                file=sys.stderr,
            )

    print(json.dumps({"orphan_count": orphan_total, "files": report}, indent=2))
    return 1 if (orphan_total and args.fail_on_orphan) else 0


if __name__ == "__main__":
    sys.exit(main())
