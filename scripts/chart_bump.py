#!/usr/bin/env python3
"""Resolve onde um chart esta' implantado e atualiza o pin nos helmfiles.

Contraparte do gitops-update.yml para CHART (nao para tag de imagem). Le a
mesma config/deployment-matrix.yml, entao a topologia — quais clusters, quais
contextos, quais sufixos de env — tem uma fonte de verdade so'.

Diferenca central em relacao ao caminho de imagem: edita `version` no
helmfile.yaml, e so' no release cujo `chart` bate EXATAMENTE com --chart-ref.
Isso e' o que impede um pin em oci://.../alpha/midaz-helm de ser sobrescrito
com a versao da linha estavel, que e' outro repositorio OCI.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from ruamel.yaml import YAML

# Canal derivado do sufixo da versao, igual ao gitops-update.yml faz com a tag.
CHANNEL_ENVS = {"beta": ["dev"], "rc": ["stg"], "stable": ["prd"]}

yaml = YAML()
yaml.preserve_quotes = True
# Helmfiles usam listas indentadas; sem isto o ruamel reescreve o arquivo
# inteiro com outro estilo e o diff fica ilegivel.
yaml.indent(mapping=2, sequence=4, offset=2)


def channel_of(version: str) -> str:
    if "-beta." in version:
        return "beta"
    if "-rc." in version:
        return "rc"
    if "-" in version:
        # alpha e outros prereleases nao promovem sozinhos: so' o ambiente que
        # ja' esta' naquele canal recebe, e isso e' decidido pelo chart-ref.
        return "beta"
    return "stable"


def load_matrix(path: Path) -> dict:
    with path.open() as handle:
        return YAML(typ="safe").load(handle)


def resolve_targets(matrix: dict, app: str, envs: list[str]) -> list[tuple[str, str]]:
    """Devolve (cluster, helmfile_env) para cada destino do app."""
    targets = []
    for cluster, config in (matrix.get("clusters") or {}).items():
        if app not in (config.get("apps") or []):
            continue

        override = (config.get("app_helmfile_env") or {}).get(app)
        if override:
            # Override aponta um diretorio fixo (ex. cross/): sufixo nao se
            # aplica e o app entra uma vez so'.
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
    """Atualiza o release que casa com chart_ref. Devolve a versao anterior."""
    with path.open() as handle:
        documents = list(yaml.load_all(handle))

    previous = None
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
                return None
            previous = current
            release["version"] = version

    if previous is None or dry_run:
        return previous

    with path.open("w") as handle:
        yaml.dump_all(documents, handle)
    return previous


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
        help="Lista de envs separada por espaco. Vazio = derivada do canal da versao.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not re.match(r"^\d+\.\d+\.\d+", args.version):
        print(f"::error::Versao nao-semver: {args.version}", file=sys.stderr)
        return 1

    channel = channel_of(args.version)
    envs = args.envs.split() if args.envs else CHANNEL_ENVS[channel]

    matrix = load_matrix(args.matrix)
    if args.app not in ((matrix.get("apps") or {}).get("registry") or []):
        print(
            f"::warning::'{args.app}' nao esta' no registry da deployment-matrix. "
            "Nada a fazer — adicione o app la' se ele deveria ser implantado.",
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
            # Ausencia e' normal: a matriz descreve a expansao maxima e nem todo
            # cluster tem todo env. Nao e' erro.
            absent.append(relative)
            continue

        previous = bump_file(path, args.chart_ref, args.version, args.dry_run)
        if previous is None:
            # chart_ref nao casou (ex. o ambiente esta' num repositorio alpha/)
            # ou ja' estava na versao alvo.
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
