#!/usr/bin/env python3
"""Resolve where a chart is deployed and update its pin in the helmfiles.

The chart-version counterpart of gitops-update.yml, which owns image tags. Both
read the same config/deployment-matrix.yml, so the topology — which clusters,
which contexts, which env suffixes — has a single source of truth.

The key difference from the image path: this edits `version` in helmfile.yaml,
and only on the release whose `chart` matches --chart-ref EXACTLY. That is what
stops an environment pinned to oci://.../alpha/midaz-helm from being overwritten
with a stable-line version, which lives in a different OCI repository.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from ruamel.yaml import YAML

# Channel derived from the version suffix, the same way gitops-update.yml reads a tag.
CHANNEL_ENVS = {"beta": ["dev"], "rc": ["stg"], "stable": ["prd"]}

yaml = YAML()
yaml.preserve_quotes = True
# Helmfiles use indented sequences; without this ruamel rewrites the whole file
# in a different style and the diff becomes unreadable.
yaml.indent(mapping=2, sequence=4, offset=2)


def channel_of(version: str) -> str:
    if "-beta." in version:
        return "beta"
    if "-rc." in version:
        return "rc"
    if "-" in version:
        # alpha and other prereleases do not promote on their own: only the
        # environment already on that channel gets it, decided by chart-ref.
        return "beta"
    return "stable"


def load_matrix(path: Path) -> dict:
    with path.open() as handle:
        return YAML(typ="safe").load(handle)


def resolve_targets(matrix: dict, app: str, envs: list[str]) -> list[tuple[str, str]]:
    """Return (cluster, helmfile_env) for every target of the app."""
    targets = []
    for cluster, config in (matrix.get("clusters") or {}).items():
        if app not in (config.get("apps") or []):
            continue

        override = (config.get("app_helmfile_env") or {}).get(app)
        if override:
            # The override points at a fixed directory (e.g. cross/): suffixes
            # do not apply and the app is deployed exactly once.
            targets.append((cluster, override))
            continue

        contexts = config.get("env_contexts") or [""]
        suffixes = config.get("env_suffixes") or [""]
        excludes = config.get("suffix_excludes_envs") or []

        for env in envs:
            for suffix in [""] if env in excludes else suffixes:
                for context in contexts:
                    leaf = f"{env}{suffix}"
                    targets.append((cluster, f"{context}/{leaf}" if context else leaf))
    return targets


def bump_file(path: Path, chart_ref: str, version: str, dry_run: bool) -> str | None:
    """Update every release matching chart_ref. Returns the previous version.

    A file may hold more than one release on the same chart. Scanning must not
    stop at the first one already sitting on the target version, or a sibling
    release would silently keep its old pin.
    """
    with path.open() as handle:
        documents = list(yaml.load_all(handle))

    previous_versions = []
    for document in documents:
        if not isinstance(document, dict):
            continue
        for release in document.get("releases") or []:
            if not isinstance(release, dict):
                continue
            if release.get("chart") != chart_ref:
                continue
            current = str(release.get("version", ""))
            if current == version:
                continue
            previous_versions.append(current)
            release["version"] = version

    if not previous_versions:
        return None
    if dry_run:
        return previous_versions[0]

    with path.open("w") as handle:
        yaml.dump_all(documents, handle)
    return previous_versions[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", required=True, type=Path)
    parser.add_argument("--gitops-root", required=True, type=Path)
    parser.add_argument("--app", required=True)
    parser.add_argument("--chart-ref", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument(
        "--envs",
        default="",
        help="Space-separated env list. Empty means derive it from the version channel.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not re.match(r"^\d+\.\d+\.\d+", args.version):
        print(f"::error::Not a semver version: {args.version}", file=sys.stderr)
        return 1

    channel = channel_of(args.version)
    envs = args.envs.split() if args.envs else CHANNEL_ENVS[channel]

    matrix = load_matrix(args.matrix)
    if args.app not in ((matrix.get("apps") or {}).get("registry") or []):
        print(
            f"::warning::'{args.app}' is not in the deployment-matrix registry. "
            "Nothing to do — add the app there if it should be deployed.",
            file=sys.stderr,
        )
        print(json.dumps({"channel": channel, "envs": envs, "changed": [], "absent": []}))
        return 0

    changed, absent, untouched = [], [], []
    for cluster, helmfile_env in resolve_targets(matrix, args.app, envs):
        path = (
            args.gitops_root
            / "environments"
            / cluster
            / "helmfile"
            / "applications"
            / helmfile_env
            / args.app
            / "helmfile.yaml"
        )
        relative = str(path.relative_to(args.gitops_root))
        if not path.is_file():
            # Absence is normal: the matrix describes the maximum expansion and
            # not every cluster has every env. Not an error.
            absent.append(relative)
            continue

        previous = bump_file(path, args.chart_ref, args.version, args.dry_run)
        if previous is None:
            # chart_ref did not match (e.g. the environment sits on an alpha/
            # repository) or it was already on the target version.
            untouched.append(relative)
            continue
        changed.append({"file": relative, "from": previous, "to": args.version})

    print(
        json.dumps(
            {
                "channel": channel,
                "envs": envs,
                "changed": changed,
                "untouched": untouched,
                "absent": absent,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
