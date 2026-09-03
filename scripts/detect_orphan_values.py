#!/usr/bin/env python3
"""Acusa chave setada no ambiente que nao existe mais no chart.

A rede que nao depende de ninguem lembrar de nada. O values.schema.json dos
charts e' permissivo — no midaz sao 106 `additionalProperties: true` contra 2
`false` — entao o `helm template` aceita chave que o chart nao conhece mais e
o deploy sobe com o default. Este check nao depende do schema nem de o autor
do chart ter escrito a migracao.

Compara as folhas do values.yaml do ambiente com as do values.yaml do chart
(obtido com `helm show values`). Chave presente no ambiente e ausente no chart
e' reportada.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

# Subarvores livres por natureza: o chart nao declara as chaves de dentro, e
# comparar folha a folha ali so' geraria falso positivo.
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
        help="Sai != 0 quando encontra orfa. Sem isto, so' relata.",
    )
    args = parser.parse_args()

    chart_keys = leaves(load(args.chart_values))
    # Prefixos validos: uma chave do ambiente e' aceita se ela, ou qualquer
    # ancestral dela, existe no chart. Cobre o caso de o chart declarar o pai
    # como mapa vazio e o ambiente preencher.
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
                f"::warning file={env_path}::`{orphan}` nao existe no chart novo. "
                "O chart vai ignorar em silencio e usar o proprio default.",
                file=sys.stderr,
            )

    print(json.dumps({"orphan_count": orphan_total, "files": report}, indent=2))
    return 1 if (orphan_total and args.fail_on_orphan) else 0


if __name__ == "__main__":
    sys.exit(main())
