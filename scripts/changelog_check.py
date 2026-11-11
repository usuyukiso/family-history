#!/usr/bin/env python3
"""Проверка страницы «Что нового» (docs/misc/changelog.md).

Ищет опубликованные страницы сайта, о которых нет строки в «Что нового»:
- страница с кодом (P1120-…, A1308-…, PLC1025-…) считается записанной,
  если код встречается в changelog.md;
- страница без кода (schemes/family-traits.md) — если в changelog.md есть
  ссылка на её файл.
Не проверяются: index.md, 404, сама changelog.md, страницы из `not_in_nav`
в mkdocs.yml (доступны только по прямой ссылке) и всё, что перечислено
в internal/changelog_baseline.txt (страницы, вошедшие в открытие сайта
одной сводной строкой, и служебные).

Запуск:
  python3 scripts/changelog_check.py            — список недостающих
  python3 scripts/changelog_check.py --init     — записать все недостающие в baseline
  python3 scripts/changelog_check.py --hook     — Stop-хук Claude Code: читает JSON
                                                   из stdin, при недостающих просит
                                                   дописать «Что нового»
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
CHANGELOG = DOCS / "misc" / "changelog.md"
BASELINE = ROOT / "internal" / "changelog_baseline.txt"
ID_RE = re.compile(r"^((?:FAM|PLC|SUR|EV|DB|P|F|D|A|B|W|N|L|I|M|V|O)\d{4})-")
SKIP = {"index.md", "404.md"}


def hidden_pages():
    text = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    m = re.search(r"^not_in_nav:\s*\|\n((?:[ \t]+.*\n)+)", text, re.M)
    if not m:
        return set()
    return {line.strip().lstrip("/") for line in m.group(1).splitlines() if line.strip()}


def baseline():
    if not BASELINE.exists():
        return set()
    return {
        line.strip()
        for line in BASELINE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }


def missing():
    log = CHANGELOG.read_text(encoding="utf-8") if CHANGELOG.exists() else ""
    hidden = hidden_pages()
    known = baseline()
    out = []
    for f in sorted(DOCS.rglob("*.md")):
        rel = f.relative_to(DOCS).as_posix()
        if f.name in SKIP or f == CHANGELOG or rel in hidden:
            continue
        m = ID_RE.match(f.name)
        key = m.group(1) if m else rel
        if key in known:
            continue
        if m:
            if re.search(rf"(?<![\w]){key}(?![\d])", log):
                continue
        elif f.name in log:
            continue
        out.append((key, rel))
    return out


def main():
    args = sys.argv[1:]
    items = missing()
    if "--init" in args:
        header = (
            "# Страницы, которые не пишутся в «Что нового» отдельной строкой\n"
            "# (вошли в открытие сайта сводно или служебные). Один код или путь в строке.\n"
        )
        old = baseline()
        keys = sorted(old | {k for k, _ in items})
        BASELINE.write_text(header + "\n".join(keys) + "\n", encoding="utf-8")
        print(f"baseline: {len(keys)} записей")
        return
    if "--hook" in args:
        try:
            data = json.load(sys.stdin)
        except Exception:
            data = {}
        if data.get("stop_hook_active") or not items:
            return
        listing = ", ".join(f"{k} ({r})" if k != r else r for k, r in items[:40])
        more = f" и ещё {len(items) - 40}" if len(items) > 40 else ""
        reason = (
            "На сайте family_tree_github есть новые страницы без строки в «Что нового» "
            f"(docs/misc/changelog.md): {listing}{more}. Добавь их под сегодняшней датой "
            "(«## D месяца YYYY», сверху): код — коротко что это ([A1308] — …; персона: "
            "[P1120](P1120) — Имя). Однотипные источники можно одной строкой. Если страница "
            "служебная и в «Что нового» не нужна — добавь её код/путь в "
            "internal/changelog_baseline.txt."
        )
        print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
        return
    for k, r in items:
        print(f"{k}\t{r}")
    if not items:
        print("Все страницы записаны в «Что нового».")


if __name__ == "__main__":
    main()
