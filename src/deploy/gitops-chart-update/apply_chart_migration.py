#!/usr/bin/env python3
"""Apply the chart-declared migration to an environment values.yaml.

A chart bump is rarely just the number. When a chart renames or removes a key,
the environment values.yaml keeps setting the old one, the chart ignores it
silently, and the deploy comes up on the chart DEFAULT. Nothing turns red.
Since that same values.yaml holds the image pin written by the dispatch, the
practical effect is losing the pin with no warning at all.

Whoever broke it knows the mapping: the chart author. So the migration ships
with the chart, in migrations/<version>.yaml:

    version: 9.0.0
    ops:
      - { op: rename, from: .ledger.image.tag, to: .midaz.ledger.image.tag }
      - { op: remove, path: .tracer }
      - { op: require, path: .midaz.database.host }

rename and remove are applied. require changes nothing: it fails the bump when
the environment lacks the key, because the new chart will not come up without it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ruamel.yaml import YAML

yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)


def split_path(dotted: str) -> list[str]:
    return [part for part in dotted.lstrip(".").split(".") if part]


def get_node(data, parts: list[str]):
    node = data
    for part in parts:
        if not isinstance(node, dict) or part not in node:
            return None, False
        node = node[part]
    return node, True


def pop_node(data, parts: list[str]):
    node = data
    for part in parts[:-1]:
        if not isinstance(node, dict) or part not in node:
            return None, False
        node = node[part]
    if not isinstance(node, dict) or parts[-1] not in node:
        return None, False
    return node.pop(parts[-1]), True


def prune_empty(data, parts: list[str]) -> None:
    """Drop the empty maps left above a key that was taken out.

    Without this, `rename .ledger.image.tag` leaves `ledger: {image: {}}` behind
    — noise in the diff, and the orphan detector then flags `ledger.image` as a
    key the chart does not know: a false positive created by the migration itself.
    """
    for depth in range(len(parts) - 1, 0, -1):
        parent, found = get_node(data, parts[:depth])
        if not found or not isinstance(parent, dict) or parent:
            break
        pop_node(data, parts[:depth])


def set_node(data, parts: list[str], value) -> None:
    node = data
    for part in parts[:-1]:
        if part not in node or not isinstance(node[part], dict):
            node[part] = {}
        node = node[part]
    node[parts[-1]] = value


REQUIRED_FIELDS = {"rename": ("from", "to"), "remove": ("path",), "require": ("path",)}


def validate(operation) -> str | None:
    """Reject a malformed op before it reaches the mutation helpers.

    Without this, `path: "."` splits to [] and pop_node raises IndexError, and a
    missing from/to raises KeyError — a raw traceback in the middle of a
    workflow that writes to a GitOps repository.
    """
    if not isinstance(operation, dict):
        return f"op is not a mapping: {operation!r}"
    kind = operation.get("op")
    if kind not in REQUIRED_FIELDS:
        return f"unknown op: {kind!r}"
    for field in REQUIRED_FIELDS[kind]:
        value = operation.get(field)
        if not isinstance(value, str) or not split_path(value):
            return f"{kind}: field {field!r} must be a non-empty key path, got {value!r}"
    return None


def apply_ops(values, ops: list[dict]) -> tuple[list[str], list[str]]:
    applied, failures = [], []
    for operation in ops:
        problem = validate(operation)
        if problem:
            failures.append(problem)
            continue
        kind = operation.get("op")

        if kind == "rename":
            source, target = split_path(operation["from"]), split_path(operation["to"])
            value, found = pop_node(values, source)
            if not found:
                # Not an error: the environment may never have set the old key
                # and simply run on the chart default.
                continue
            prune_empty(values, source)
            set_node(values, target, value)
            applied.append(f"rename {operation['from']} -> {operation['to']}")

        elif kind == "remove":
            parts = split_path(operation["path"])
            _, found = pop_node(values, parts)
            if found:
                prune_empty(values, parts)
                applied.append(f"remove {operation['path']}")

        elif kind == "require":
            _, found = get_node(values, split_path(operation["path"]))
            if not found:
                failures.append(
                    f"require {operation['path']}: missing in this environment, no chart default"
                )

    return applied, failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--migration", required=True, type=Path)
    parser.add_argument("--values", required=True, type=Path, nargs="+")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.migration.is_file():
        # No migration file means a plain bump. Normal for patch and minor.
        print(json.dumps({"migration": None, "results": []}))
        return 0

    with args.migration.open() as handle:
        migration = YAML(typ="safe").load(handle) or {}

    # A YAML document is not necessarily a mapping. A list root reaches .get()
    # and raises AttributeError, printing a traceback instead of the structured
    # error the caller can act on.
    if not isinstance(migration, dict):
        print(
            f"::error file={args.migration}::migration root must be a mapping, "
            f"got {type(migration).__name__}",
            file=sys.stderr,
        )
        return 1
    ops = migration.get("ops") or []
    if not isinstance(ops, list):
        print(
            f"::error file={args.migration}::`ops` must be a list, "
            f"got {type(ops).__name__}",
            file=sys.stderr,
        )
        return 1

    results, failed = [], False
    for values_path in args.values:
        if not values_path.is_file():
            continue
        with values_path.open() as handle:
            values = yaml.load(handle) or {}

        applied, failures = apply_ops(values, ops)
        if failures:
            failed = True
        if applied and not args.dry_run:
            with values_path.open("w") as handle:
                yaml.dump(values, handle)

        results.append({"file": str(values_path), "applied": applied, "failures": failures})

    print(json.dumps({"migration": str(args.migration), "results": results}, indent=2))

    for result in results:
        for failure in result["failures"]:
            print(f"::error file={result['file']}::{failure}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
