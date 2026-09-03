#!/usr/bin/env python3
"""Aplica a migracao declarada pelo chart sobre o values.yaml do ambiente.

Um bump de chart raramente e' so' o numero. Quando o chart renomeia ou remove
uma chave, o values.yaml do ambiente continua setando a chave velha, o chart
ignora em silencio e o deploy sobe com o DEFAULT do chart. Nada fica vermelho.
Como e' nesse values.yaml que mora o pin de imagem escrito pelo dispatch, o
efeito pratico e' perder o pin sem nenhum sinal.

Quem sabe o mapeamento e' quem quebrou: o autor do chart. Por isso a migracao
e' declarada no proprio chart, em migrations/<versao>.yaml:

    version: 9.0.0
    ops:
      - { op: rename, from: .ledger.image.tag, to: .midaz.ledger.image.tag }
      - { op: remove, path: .tracer }
      - { op: require, path: .midaz.database.host }

rename/remove sao aplicados. require nao altera nada: falha o bump se o
ambiente nao tiver a chave, porque o chart novo nao sobe sem ela.
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
    """Remove os mapas vazios que sobram acima de uma chave retirada.

    Sem isto, `rename .ledger.image.tag` deixa `ledger: {image: {}}` no arquivo
    — sujeira no diff, e o detector de orfas acusa `ledger.image` como chave que
    o chart nao conhece, um falso positivo criado pela propria migracao.
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


def apply_ops(values, ops: list[dict]) -> tuple[list[str], list[str]]:
    applied, failures = [], []
    for operation in ops:
        kind = operation.get("op")

        if kind == "rename":
            source, target = split_path(operation["from"]), split_path(operation["to"])
            value, found = pop_node(values, source)
            if not found:
                # Nao e' erro: o ambiente pode nunca ter setado a chave antiga e
                # estar rodando no default do chart.
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
                    f"require {operation['path']}: ausente neste ambiente e sem default no chart"
                )

        else:
            failures.append(f"op desconhecida: {kind!r}")

    return applied, failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--migration", required=True, type=Path)
    parser.add_argument("--values", required=True, type=Path, nargs="+")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.migration.is_file():
        # Sem arquivo de migracao o bump e' puro. Caso normal para patch/minor.
        print(json.dumps({"migration": None, "results": []}))
        return 0

    with args.migration.open() as handle:
        migration = YAML(typ="safe").load(handle) or {}
    ops = migration.get("ops") or []

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
