"""Схема ближайшей родни на странице персоны: родители → человек с братьями и сёстрами → дети.

Хук MkDocs. Перед разделом «## Источники» (если его нет — в конец страницы)
вставляется схема из трёх столбцов, слева направо по поколениям:

    Родители          Братья и сёстры          Дети
    [отец]  ─┐        [брат]                   ┌─ [сын]
    [мать]  ─┘        [ЧЕЛОВЕК] 💍 [супруг]  ──┤  [дочь]
                      [сестра]                 └─ [сын]

Берутся только родители (не их братья и сёстры), все известные братья и сёстры,
супруги и все известные дети. Люди со страницей — из полей `parents`, `spouses`,
`children` (связь с одной стороны считается и для другой); у них карточка — ссылка
на страницу. Люди без своей страницы (известны только из текста биографии)
записываются в front matter:

    children_no_page:            # дети без своей страницы
      - {name: "Февронья", years: "ок. 1734", sex: f}
      - {name: "Тихон [?]", years: "1766", sex: m, note: "по-видимому"}
    siblings_no_page:            # братья и сёстры, которых нет в children_no_page родителей
      - {name: "Прасковья", years: "ок. 1743", sex: f}

Братья и сёстры = все дети родителей (со страницей и из `children_no_page` обоих
родителей) + свои `siblings_no_page`; одинаковые записи (имя + годы) склеиваются.
Если оба родителя на сайте, а брат записан только у одного, он подписан
«единокровный» (общий отец) или «единоутробный» (общая мать).

Родители не установлены, но есть разбор с предположениями — в столбце «Родители»
вместо «не известны» ставится карточка-ссылка на него:

    parents_hypothesis:
      label: "Предполагаемые родители"
      link: "puzzles/sychevy-v-shevelevke.md#predpolozheniya"   # путь от docs/
      note: "предположения о родстве"                            # необязательно

Родившиеся после 1950 года (первый год в `birth_date` / `years`) и страницы
`living: true` в схему не попадают. Схемы нет на скрытых страницах (`hidden: true`)
и на страницах вне древа (`in_tree: false`), но такие люди, если страница не скрыта,
показываются в чужих схемах ссылкой.
"""

import html
import posixpath
import re

import yaml
from mkdocs.structure.toc import AnchorLink
from mkdocs.utils import get_relative_url

FILE_ID = re.compile(r"^(P\d{4})-")
H1 = re.compile(r"^#\s+(.+?)\s*$", re.M)
YEARS = re.compile(r"^(.*\S)\s+\(([^()]*[\d?][^()]*)\)$")
YEAR = re.compile(r"\d{4}")
SOURCES_H2 = re.compile(r"<h2[^>]*>\s*Источники")
RELATED_H2 = re.compile(r"<h2[^>]*>\s*Связанные персоны")
LAST_YEAR = 1950  # родившихся позже не показываем
SPOUSE = "💍"

_people = {}  # ID -> dict


def _front_matter(text):
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    try:
        return yaml.safe_load(parts[1]) or {}, parts[2]
    except yaml.YAMLError:
        return {}, parts[2]


def _ids(value):
    return [v for v in (value or []) if isinstance(v, str)]


def _year(value):
    m = YEAR.search(str(value or ""))
    return int(m.group(0)) if m else None


def _no_page(value):
    """Список записей `{name, years, sex, note}` из front matter."""
    out = []
    for i, e in enumerate(value or []):
        if isinstance(e, str):
            e = {"name": e}
        if not isinstance(e, dict) or not e.get("name"):
            continue
        years = str(e.get("years") or "").strip()
        out.append({
            "pid": None,
            "name": str(e["name"]).strip(),
            "years": years,
            "village": "",
            "female": str(e.get("sex") or "") == "f",
            "note": str(e.get("note") or "").strip(),
            "born": _year(years),
            "sort": None,
            "order": i,
        })
    # Год неизвестен — для порядка берём год соседа по списку (предыдущего, иначе
    # следующего), чтобы человек остался там, где его поставил составитель.
    known = [e["born"] for e in out]
    for i, e in enumerate(out):
        if e["born"] is None:
            before = [y for y in known[:i] if y is not None]
            after = [y for y in known[i + 1:] if y is not None]
            e["sort"] = before[-1] if before else (after[0] if after else None)
    return out


def on_files(files, config):
    _people.clear()
    for f in files.documentation_pages():
        m = FILE_ID.match(posixpath.basename(f.src_uri))
        if not m or not f.src_uri.startswith("people/"):
            continue
        meta, body = _front_matter(f.content_string)
        if meta.get("hidden"):
            continue
        h1 = H1.search(body)
        title = h1.group(1) if h1 else str(meta.get("name") or m.group(1))
        ym = YEARS.match(title)
        name, years = (ym.group(1), ym.group(2)) if ym else (title, "")
        born = _year(meta.get("birth_date")) or _year(meta.get("sort_year"))
        _people[m.group(1)] = {
            "pid": m.group(1),
            "file": f,
            "name": name,
            "years": years,
            "village": str(meta.get("village") or ""),
            "female": meta.get("sex") == "f",
            "note": "",
            "born": born,
            "order": 0,
            "in_tree": meta.get("in_tree") is not False,
            "living": bool(meta.get("living")),
            "first_parents": _ids(meta.get("parents")),
            "parents": set(_ids(meta.get("parents"))),
            "spouses": set(_ids(meta.get("spouses"))),
            "children": set(_ids(meta.get("children"))),
            "kids_np": _no_page(meta.get("children_no_page")),
            "sibs_np": _no_page(meta.get("siblings_no_page")),
            "parents_hypothesis": meta.get("parents_hypothesis") if isinstance(meta.get("parents_hypothesis"), dict) else None,
        }
    for pid, p in _people.items():
        for key in ("parents", "spouses", "children"):
            p[key] &= _people.keys()
        for c in p["children"]:
            _people[c]["parents"].add(pid)
        for par in p["parents"]:
            _people[par]["children"].add(pid)
        for s in p["spouses"]:
            _people[s]["spouses"].add(pid)
    return files


def _shown(e):
    if e["pid"] and _people[e["pid"]]["living"]:
        return False
    return e["born"] is None or e["born"] <= LAST_YEAR


def _key(e):
    y = e["born"] if e["born"] is not None else e.get("sort")
    return (y if y is not None else 9999, e["order"], e["name"])


def _dedupe(entries):
    seen, out = {}, []
    for e in entries:
        k = e["pid"] or (e["name"], e["years"])
        if k not in seen:
            seen[k] = e
            out.append(e)
        elif seen[k].get("sort") is None and e.get("sort") is not None:
            # тот же человек у другого родителя: там известно, где он стоит по порядку
            out[out.index(seen[k])] = seen[k] = e
    return out


def _kids(pid):
    """Все дети человека: со страницей и без."""
    p = _people[pid]
    return [_people[c] for c in p["children"]] + p["kids_np"]


def _card(e, page, cls="", extra=""):
    sex = "kin-f" if e["female"] else "kin-m"
    years = f'<span class="kin-years">{html.escape(e["years"])}</span>' if e["years"] else ""
    village = f'<span class="kin-place">{html.escape(e["village"])}</span>' if e["village"] else ""
    note = f'<span class="kin-note">{html.escape(e["note"])}</span>' if e["note"] else ""
    inner = f'<span class="kin-name">{html.escape(e["name"])}</span>{village}{years}{note}{extra}'
    if e["pid"] and "kin-self" not in cls:
        href = get_relative_url(e["file"].url, page.url)
        return f'<a class="kin-card {sex} {cls}" href="{href}">{inner}</a>'
    nopage = "" if e["pid"] else " kin-nopage"
    return f'<span class="kin-card {sex}{nopage} {cls}">{inner}</span>'


LEGEND = (
    '<div class="kin-legend">'
    '<span><i class="kin-sw kin-sw--m"></i><i class="kin-sw kin-sw--f"></i>есть своя страница — нажмите, чтобы перейти '
    '(голубой — мужчина, жёлтый — женщина)</span>'
    '<span><i class="kin-sw kin-sw--nopage"></i>отдельной страницы нет, упоминается только в биографиях семьи</span>'
    '<span><i class="kin-sw kin-sw--self"></i>тот, чья это страница</span>'
    f'<span>{SPOUSE} супруг(а)</span>'
    '<span><i class="kin-sw kin-sw--line"></i>линии ведут от родителей к детям</span>'
    '</div>'
)


def _scheme(pid, page, files):
    p = _people[pid]
    # Родители: отец, затем мать
    parents = sorted((_people[x] for x in p["parents"]), key=lambda e: (e["female"], _key(e)))
    father = next((e["pid"] for e in parents if not e["female"]), None)
    mother = next((e["pid"] for e in parents if e["female"]), None)

    # Братья и сёстры вместе с самим человеком — по году рождения
    sibs = []
    for par in parents:
        sibs += [e for e in _kids(par["pid"])]
    sibs += p["sibs_np"]
    sibs = [e for e in _dedupe(sibs) if e.get("pid") != pid]
    sibs = [e for e in sibs if _shown(e)]
    # «единокровный» / «единоутробный», если общий только один из двух родителей;
    # записи без страницы сравниваем по (имя, годы)
    def same(a, b):
        return a is b or (not a["pid"] and not b["pid"] and (a["name"], a["years"]) == (b["name"], b["years"]))

    def half(e):
        if not (father and mother):
            return ""
        in_f = any(same(e, x) for x in _kids(father))
        in_m = any(same(e, x) for x in _kids(mother))
        if in_f == in_m:
            return ""
        end = "ая" if e["female"] else "ый"
        return f'<span class="kin-note">{"единокровн" if in_f else "единоутробн"}{end}</span>'

    middle = sorted(sibs + [p], key=_key)

    kids = [e for e in _dedupe(_kids(pid)) if _shown(e)]
    kids.sort(key=_key)

    # --- столбцы
    hypo = p["parents_hypothesis"]
    if parents:
        col1 = "".join(_card(e, page) for e in parents)
    elif hypo and hypo.get("link"):
        # родители не установлены, но есть разбор с предположениями — ссылка на него
        path, _, anchor = str(hypo["link"]).partition("#")
        target = files.get_file_from_path(path)
        href = get_relative_url(target.url, page.url) + (f"#{anchor}" if anchor else "") if target else "#"
        label = html.escape(str(hypo.get("label") or "Предполагаемые родители"))
        note = html.escape(str(hypo.get("note") or "предположения о родстве"))
        col1 = (f'<a class="kin-card kin-m kin-nopage kin-hypo" href="{href}">'
                f'<span class="kin-name">{label}</span><span class="kin-note">{note} →</span></a>')
    else:
        col1 = '<span class="kin-card kin-nopage kin-empty">не известны</span>'

    rows = []
    for e in middle:
        if e is p:
            spouses = sorted((_people[s] for s in p["spouses"] if _shown(_people[s])), key=_key)
            sp = "".join(
                f'<div class="kin-spouse"><span class="kin-ring" title="в браке с">{SPOUSE}</span>{_card(s, page)}</div>'
                for s in spouses
            )
            rows.append(f'<div class="kin-selfbox">{_card(e, page, "kin-self")}{sp}</div>')
        else:
            rows.append(_card(e, page, "", half(e)))
    col2 = "".join(rows)

    if kids:
        col3 = "".join(_card(e, page) for e in kids)
    else:
        col3 = '<span class="kin-empty-text">не известны</span>'

    head2 = "Братья и сёстры" if sibs else ("Она" if p["female"] else "Он")
    return (
        '<div class="kin-nav" id="rodnya">'
        '<div class="kin-title">Родители, братья и сёстры, дети</div>'
        f'{LEGEND}'
        '<div class="kin-grid">'
        f'<div class="kin-col kin-col--parents"><div class="kin-head">Родители</div>'
        f'<div class="kin-stack{"" if parents else " kin-stack--none"}">{col1}</div></div>'
        f'<div class="kin-col kin-col--middle"><div class="kin-head">{head2}</div>'
        f'<div class="kin-stack{"" if parents else " kin-stack--none"}{" kin-has-kids" if kids else ""}">{col2}</div></div>'
        f'<div class="kin-col kin-col--kids"><div class="kin-head">Дети</div>'
        f'<div class="kin-stack{"" if kids else " kin-stack--none"}">{col3}</div></div>'
        '</div></div>\n'
    )


def on_page_content(output, page, config, files):
    m = FILE_ID.match(posixpath.basename(page.file.src_uri))
    if not m or not page.file.src_uri.startswith("people/"):
        return output
    p = _people.get(m.group(1))
    if not p or not p["in_tree"] or p["living"]:
        return output
    block = _scheme(p["pid"], page, files)
    # перед «Источниками»; если их нет — перед «Связанными персонами»; иначе в конец
    hit = SOURCES_H2.search(output) or RELATED_H2.search(output)
    _add_toc_item(page)
    return output[: hit.start()] + block + output[hit.start():] if hit else output + "\n" + block


TOC_TITLE = "Родители, братья и сёстры, дети"


def _add_toc_item(page):
    """Пункт схемы в правом оглавлении — на том же месте, что и схема на странице."""
    toc = page.toc
    if toc is None:
        return
    items = list(toc.items)
    # заголовки h2 обычно лежат внутри единственного h1
    if len(items) == 1 and items[0].level == 1:
        level, siblings = 2, items[0].children
    else:
        level, siblings = (items[0].level if items else 2), toc.items
    if any(getattr(x, "id", "") == "rodnya" for x in siblings):
        return
    link = AnchorLink(TOC_TITLE, "rodnya", level)
    for i, x in enumerate(siblings):
        if x.title.strip().startswith(("Источники", "Связанные персоны")):
            siblings.insert(i, link)
            return
    siblings.append(link)
