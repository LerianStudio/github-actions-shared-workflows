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


LEVELS = {"major": 3, "minor": 2, "patch": 1, "none": 0}

# The grammar from semver.org, with an optional leading `v` because some charts
# publish that way (cert-manager ships v1.21.1). A looser `\d+\.\d+\.\d+` accepts
# `1.2.3-`, `1.2.3+` and `01.2.3`, and those would be written verbatim into every
# matching release.
SEMVER = re.compile(
    r"^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


def parse_version(value: str):
    """(major, minor, patch, is_stable) or None when it is not semver."""
    match = SEMVER.fullmatch(str(value))
    if not match:
        return None
    major, minor, patch, prerelease, _build = match.groups()
    return (int(major), int(minor), int(patch), prerelease is None)


def transition_level(previous: str, target: str) -> str:
    """Classify one from -> to transition."""
    a, b = parse_version(previous), parse_version(target)
    if not a or not b:
        # A pin that is not semver cannot be proven safe, so treat it as the most
        # restrictive case rather than silently routing it as a patch.
        return "major"
    if a[0] != b[0]:
        return "major"
    if a[1] != b[1]:
        return "minor"
    if a[2] != b[2] or a[3] != b[3]:
        return "patch"
    return "none"


def bump_file(path: Path, chart_ref: str, version: str, dry_run: bool) -> list[str]:
    """Update every release matching chart_ref. Returns each previous version.

    A file may hold more than one release on the same chart, and they can sit on
    different pins. Returning only the first would let a 1.1.0 -> 2.10.0 jump be
    classified by a 2.9.0 -> 2.10.0 sibling, so every transition comes back and
    the caller keeps the most restrictive one.
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

    if not previous_versions or dry_run:
        return previous_versions

    with path.open("w") as handle:
        yaml.dump_all(documents, handle)
    return previous_versions


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

    # fullmatch, not match: a prefix check accepts "1.2.3invalid" and the CLI
    # would then write that string into every matching release.
    if not SEMVER.fullmatch(args.version):
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

        previous_versions = bump_file(path, args.chart_ref, args.version, args.dry_run)
        if not previous_versions:
            # chart_ref did not match (e.g. the environment sits on an alpha/
            # repository) or it was already on the target version.
            untouched.append(relative)
            continue
        # Most restrictive transition within this file wins, and `from` reports
        # the pin that produced it — not whichever release came first.
        levels = [transition_level(v, args.version) for v in previous_versions]
        worst = max(levels, key=lambda name: LEVELS[name])
        changed.append(
            {
                "file": relative,
                "from": previous_versions[levels.index(worst)],
                "to": args.version,
                "level": worst,
            }
        )

    # The most restrictive transition across every environment decides routing.
    # Environments drift apart — fetcher sits at 3.1.0 in dev-st and
    # 2.2.0-beta.2 in prd-st — so reading the level off a single entry can route
    # a major jump into production as a patch.
    level = max(
        (row["level"] for row in changed),
        key=lambda name: LEVELS[name],
        default="none",
    )

    print(
        json.dumps(
            {
                "channel": channel,
                "envs": envs,
                "level": level,
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
