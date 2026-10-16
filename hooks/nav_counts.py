"""Счётчики в левом меню.

- У каждого места (раздел «Места») — число связанных жителей: персоны из `people:`
  в front matter страницы места плюс строки таблицы «Другие жители и связанные люди».
  При наведении — подсказка «связанных жителей».
- У раздела «Персоны» — число персон с отдельной страницей, которые стоят в
  родословном древе (прямые предки): без скрытых страниц (`hidden: true`) и без
  страниц с `in_tree: false`. При наведении — подсказка «персон в древе».
- У каждой группы источников (раздел «Источники»: «Архивные записи», «Книги», …) —
  число источников в группе, без подсказки.
- У каждой фамилии (раздел «Фамилии») — число персон из `people:` в front matter
  страницы фамилии, с подсказкой «персон».
- У каждой губернии в разделе «Места» — число мест в ней, с подсказкой «мест».

Значок оформлен так же, как число детей в родословном древе (`ftree-count`).
Вставляется в готовый HTML меню (on_post_page), поэтому заголовки страниц
(<title>, поиск) не меняются.
"""

import html
import re

import yaml
from mkdocs.structure.nav import Section
from mkdocs.structure.pages import Page

_places = {}  # название места -> число жителей
_surnames = {}  # фамилия -> число персон
_groups = {}  # группа источников или губерния -> (число страниц, подсказка)
_persons = 0  # персоны в древе (раздел «Персоны»)


def _front_matter(text):
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    try:
        return yaml.safe_load(parts[1]) or {}, parts[2]
    except yaml.YAMLError:
        return {}, parts[2]


def _residents(text):
    meta, body = _front_matter(text)
    people = set(meta.get("people") or [])
    others = 0
    m = re.search(r"^### Другие жители и связанные люди\s*$(.*?)(?=^## |\Z)", body, re.M | re.S)
    if m:
        rows = [l for l in m.group(1).splitlines() if l.startswith("|")]
        for row in rows[2:]:  # без шапки и разделителя
            first = row.strip("|").split("|")[0].strip()
            if first and first != "—":
                others += 1
    return len(people) + others


def on_files(files, config):
    global _persons
    _places.clear()
    _surnames.clear()
    _persons = 0
    for f in files.documentation_pages():
        if re.match(r"people/P\d{4}-", f.src_uri):
            meta, _ = _front_matter(f.content_string)
            if not meta.get("hidden") and meta.get("in_tree") is not False:
                _persons += 1
        if re.match(r"places/PLC\d{4}-", f.src_uri):
            text = f.content_string
            meta, _ = _front_matter(text)
            if meta.get("name"):
                _places[str(meta["name"])] = _residents(text)
        if re.match(r"surnames/SUR\d{4}-", f.src_uri):
            meta, _ = _front_matter(f.content_string)
            if meta.get("name"):
                _surnames[str(meta["name"])] = len(meta.get("people") or [])
    return files


def on_nav(nav, config, files):
    _groups.clear()
    for item in nav.items:
        if isinstance(item, Section) and item.title in ("Источники", "Места"):
            hint = "мест" if item.title == "Места" else None
            for group in item.children:
                if isinstance(group, Section):
                    _groups[group.title] = (sum(1 for c in group.children if isinstance(c, Page)), hint)
    return nav


def _badge(n, title=None):
    t = f' title="{html.escape(title)}"' if title else ""
    cls = "nav-count nav-count--hint" if title else "nav-count"
    return f'<span class="{cls}"{t}>{n}</span>'


def _insert(output, name, badge, tag=None):
    pat = re.compile(
        (rf"(<{tag} " if tag else "(")
        + r'class="md-nav__link[^"]*"[^>]*>\s*<span class="md-ellipsis">\s*'
        + re.escape(html.escape(name, quote=False))
        + r"\s*</span>)"
    )
    return pat.sub(lambda m: m.group(1) + badge, output)


def on_post_page(output, page, config):
    if _persons:
        output = _insert(output, "Персоны", _badge(_persons, "персон в древе"))
    for name, n in _places.items():
        output = _insert(output, name, _badge(n, "связанных жителей"))
    for name, n in _surnames.items():
        output = _insert(output, name, _badge(n, "персон"))
    # Группы — только заголовки разделов меню (<label>), не ссылки оглавления:
    # там бывают одноимённые заголовки, например «Псковская губерния» на странице «Места».
    for name, (n, hint) in _groups.items():
        output = _insert(output, name, _badge(n, hint), tag="label")
    return output
