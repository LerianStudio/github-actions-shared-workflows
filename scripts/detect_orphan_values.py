#!/usr/bin/env python3
"""Flag a key set in an environment that no longer exists in the chart.

The safety net that depends on nobody remembering anything. The charts'
values.schema.json is permissive — midaz has 106 `additionalProperties: true`
against 2 `false` — so `helm template` happily accepts a key the chart no longer
knows and the deploy comes up on the default. This check needs neither the schema
nor the chart author having written a migration.

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

    chart_keys = leaves(load(args.chart_values))
    # Valid prefixes: an environment key is accepted when it, or any ancestor of
    # it, exists in the chart. Covers the chart declaring the parent as an empty
    # map and the environment filling it in.
    prefixes = {key.rsplit(".", index)[0] for key in chart_keys for index in range(key.count(".") + 1)}

    report, orphan_total = [], 0
    for env_path in args.env_values:
        if not env_path.is_file():
            continue
        orphans = sorted(
            key
            for key in leaves(load(env_path))
            if key not in chart_keys and key not in prefixes
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
