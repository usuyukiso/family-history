"""Навигация «Предыдущий / Следующий известный год» на страницах источников.

Источник, который даёт список семей деревни (исповедная роспись, перепись,
ревизская сказка, книга выбывших душ, похозяйственная книга — НЕ метрики),
помечается в front matter:

    family_list: [PLC1015]          # деревни, по которым здесь есть список семей

Хук собирает все такие страницы, для каждой деревни раскладывает их по годам
(первые 4 цифры `document_date`) и перед «## Связанные персоны» (если раздела
нет — в конец страницы) вставляет карточку: предыдущий и следующий источник
по той же деревне. Порядок — по году, внутри одного года по алфавиту вида
документа (исповедная роспись раньше ревизской сказки), затем по ID.
Включаются все списки семей, даже где наших нет. Промежуточный источник появился — карточки
пересчитываются сами при сборке, руками ничего править не нужно.
"""

import html as _html
import posixpath
import re

import yaml
from mkdocs.utils import get_relative_url

FILE_ID = re.compile(r"^((?:PLC|A|B|D|F|L|W|DB)\d{4})-")
YEAR = re.compile(r"(\d{4})")
RELATED = re.compile(r'<h2[^>]*>\s*Связанные персоны')

_lists = {}   # PLC -> [(year, sid, src_uri, title, kind)]
_places = {}  # PLC -> (src_uri, подпись «д. Горелик»)
_by_sid = {}  # sid -> (year, [PLC…])

TYPE_SHORT = {"деревня": "д.", "село": "с.", "хутор": "х.", "посёлок": "пос.", "поселок": "пос."}


def _front_matter(text):
    if not text.startswith("---"):
        return {}
    try:
        return yaml.safe_load(text.split("---", 2)[1]) or {}
    except yaml.YAMLError:
        return {}


def _kind(title):
    """Вид документа по названию источника: «Исповедная роспись», «Ревизская сказка (III ревизия)»…"""
    t = title.lower()
    rev = re.search(r"\(([ivx]+ ревизия)\)", t)
    rev = f" ({rev.group(1).upper().replace(' РЕВИЗИЯ', ' ревизия')})" if rev else ""
    if "исповед" in t:
        return "Исповедная роспись"
    if "похоз" in t:
        return "Похозяйственная книга"
    if "выбывш" in t:
        return "Книга выбывших душ" + rev
    if "перепис" in t:
        return "Переписная книга" + rev
    if "сказк" in t or "ревиз" in t:
        return "Ревизская сказка" + rev
    return "Список семей"


def on_files(files, config):
    _lists.clear(), _places.clear(), _by_sid.clear()
    for f in files.documentation_pages():
        m = FILE_ID.match(posixpath.basename(f.src_uri))
        if not m:
            continue
        sid = m.group(1)
        meta = _front_matter(f.content_string)
        if sid.startswith("PLC"):
            short = TYPE_SHORT.get(str(meta.get("place_type", "")).strip(), "")
            _places[sid] = (f.src_uri, f"{short} {meta.get('name', sid)}".strip())
            continue
        plcs = meta.get("family_list") or []
        if isinstance(plcs, str):
            plcs = [plcs]
        y = YEAR.search(str(meta.get("document_date", "")))
        if not plcs or not y:
            continue
        title = str(meta.get("title", sid))
        year = int(y.group(1))
        _by_sid[sid] = (year, list(plcs))
        for plc in plcs:
            _lists.setdefault(str(plc), []).append((year, sid, f.src_uri, title, _kind(title)))
    return files


def _row(page, files, arrow, label, entry):
    year, sid, src_uri, title, kind = entry
    target = files.get_file_from_path(src_uri)
    href = get_relative_url(target.url, page.url) if target else "#"
    return (
        f'<a class="fl-nav__row" href="{href}" title="{_html.escape(title)}">'
        f'<span class="fl-nav__arrow" aria-hidden="true">{arrow}</span>'
        f'<span class="fl-nav__text"><span class="fl-nav__label">{label}</span>'
        f'<span class="fl-nav__meta">{year} · {_html.escape(kind)} · {sid}</span></span>'
        f'<span class="fl-nav__badge">Источник</span></a>'
    )


def on_page_content(html, page, config, files):
    m = FILE_ID.match(posixpath.basename(page.file.src_uri))
    if not m or m.group(1) not in _by_sid:
        return html
    sid = m.group(1)
    year, plcs = _by_sid[sid]
    blocks = []
    for plc in plcs:
        # одна цепочка: по году, внутри года — по алфавиту вида документа, затем по ID
        chain = sorted(_lists.get(str(plc), []), key=lambda e: (e[0], e[4], e[1]))
        i = next((k for k, e in enumerate(chain) if e[1] == sid), None)
        if i is None:
            continue
        prev = [chain[i - 1]] if i > 0 else []
        nxt = [chain[i + 1]] if i + 1 < len(chain) else []
        if not prev and not nxt:
            continue
        rows = [_row(page, files, "←", "Предыдущий известный год", e) for e in prev]
        rows += [_row(page, files, "→", "Следующий известный год", e) for e in nxt]
        caption = ""
        if len(plcs) > 1 and plc in _places:
            p_uri, p_name = _places[plc]
            p_file = files.get_file_from_path(p_uri)
            p_href = get_relative_url(p_file.url, page.url) if p_file else "#"
            caption = f'<div class="fl-nav__caption"><a href="{p_href}">{_html.escape(p_name)}</a></div>'
        blocks.append(f'{caption}<nav class="fl-nav" aria-label="Другие годы">{"".join(rows)}</nav>')
    if not blocks:
        return html
    block = f'<div class="fl-nav-wrap">{"".join(blocks)}</div>\n'
    hit = RELATED.search(html)
    return html[: hit.start()] + block + html[hit.start():] if hit else html + "\n" + block
