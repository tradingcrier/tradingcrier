#!/usr/bin/env python3
"""Собирает catalog.json (tradingcrier.catalog/1) из файлов спек.

Приложение сверяет sha256 скачанного файла с индексом, поэтому индекс надо
пересобирать после ЛЮБОГО изменения спек:

    python build_catalog.py --repo OWNER/REPO [--branch main] [--dir .]

Хэш считается по байтам с переводами строк LF — совпадает с тем, что отдаёт
raw.githubusercontent.com при .gitattributes «*.json text eol=lf».

Проверка, что индекс совпадает с уже опубликованными файлами:

    python build_catalog.py --repo OWNER/REPO --check

Необязательный catalog.meta.json рядом со спеками:
    {"broker_rest_v2.json": {"summary": "…", "hidden": true}}
"""

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

SCHEMA_PREFIX = "tradingcrier.source/"
CATALOG_SCHEMA = "tradingcrier.catalog/1"
RAW_BASE = "https://raw.githubusercontent.com/{repo}/{branch}"


def spec_files(root: Path, hidden: set[str]) -> list[Path]:
    out = []
    for p in sorted(root.glob("*.json")):
        if p.name in ("catalog.json", "catalog.meta.json") or p.name in hidden:
            continue
        try:
            head = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if str(head.get("schema", "")).startswith(SCHEMA_PREFIX):
            out.append(p)
    return out


def sha256_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def build(root: Path, base: str, meta: dict) -> dict:
    specs = []
    for p in spec_files(root, {k for k, v in meta.items() if v.get("hidden")}):
        head = json.loads(p.read_text(encoding="utf-8"))
        entry = {
            "name": head.get("name", ""),
            "version": head.get("version", ""),
            "url": f"{base}/{p.name}",
            "sha256": sha256_lf(p),
            "minEngine": head.get("minEngine", ""),
            "summary": meta.get(p.name, {}).get("summary", ""),
        }
        specs.append(entry)
        print(f"  {p.name}: {entry['name']} {entry['version']} sha256={entry['sha256'][:12]}…")
    return {"schema": CATALOG_SCHEMA, "specs": specs}


def check(index: dict) -> int:
    """Скачивает каждую url и сверяет sha256 с записанным в индексе."""
    bad = 0
    for e in index["specs"]:
        try:
            with urllib.request.urlopen(e["url"], timeout=15) as r:
                got = hashlib.sha256(r.read()).hexdigest()
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL {e['url']}: {exc}")
            bad += 1
            continue
        ok = got == e["sha256"]
        print(f"  {'ok  ' if ok else 'FAIL'} {e['name']}: {e['url']}")
        bad += 0 if ok else 1
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True, help="OWNER/REPO на GitHub")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--dir", default=".", help="папка со спеками (по умолчанию текущая)")
    ap.add_argument("--check", action="store_true", help="только проверить опубликованные файлы")
    args = ap.parse_args()

    root = Path(args.dir)
    base = RAW_BASE.format(repo=args.repo, branch=args.branch)
    meta_path = root / "catalog.meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}

    index_path = root / "catalog.json"
    if args.check:
        index = json.loads(index_path.read_text(encoding="utf-8"))
        return check(index)

    index = build(root, base, meta)
    index_path.write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"\nЗаписано {index_path} ({len(index['specs'])} спек)")
    print("Закоммитьте catalog.json вместе со спеками — sha256 в индексе")
    print("должен совпадать с байтами, которые отдаёт raw.githubusercontent.com.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
