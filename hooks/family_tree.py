"""Родословное древо: раскрывающийся список «человек → супруги → дети → …».

Хук MkDocs. Связи берутся из front matter страниц персон (`parents`, `spouses`,
`children`); связь, записанная хотя бы с одной стороны, считается и для другой
(если у сына `parents: [P1017]`, он попадёт в дети P1017, даже когда у того
`children: []`). Скрытые страницы (`hidden: true`) в древо не попадают.
Страница с `in_tree: false` (человек не записан ни в одном документе, известен,
например, только по отчеству ребёнка) остаётся на сайте и доступна по ссылкам,
но в древо и в левое меню не попадает.

На странице, где стоит строка `<!-- family-tree -->`, она заменяется деревом.
Корни древа — люди без родителей среди персон сайта; человек, который сам без
родителей, но состоит в браке с кем-то, у кого родители есть, отдельным корнем
не показывается (он виден рядом с супругом). Если оба супруга без родителей,
корнем стоит тот, у кого больше детей на сайте, при равенстве — муж (поле
`sex: m|f` в front matter); жена видна рядом с ним. Человек с двумя известными
родителями виден в обеих ветвях — по отцу и по матери.

Корни разложены по вкладкам («Псковская ветка», …): вкладку задаёт поле
`tree_branch` в front matter корня (или его супруга без родителей); корни без
этого поля попадают во вкладку «Другие». Вкладки идут по алфавиту, «Другие» — последней.

Имя и годы жизни берутся из заголовка страницы: «# Иван Давыдов (ок. 1815 – 1901)».
Под именем — где жил человек, из поля `village` («д. Горелик → Захарино»);
в древе это вторая строка, в левом меню — мелкая строка под подписью.

Тот же порядок хук строит в левом меню, в разделе «Персоны» (см. on_nav): имя
открывает страницу, стрелка рядом раскрывает супругов и детей. В меню каждая
страница стоит один раз — под первым родителем из её `parents` (обычно отец);
в другой ветви (у матери) и у супруга из другой семьи она дана ссылкой «↗» / «💍».
Подписи берутся из `nav` в mkdocs.yml; для страницы, которой там нет, —
«год имя».
"""

import html
import posixpath
import re

import yaml
from mkdocs.structure.nav import (
    Link,
    Section,
    _add_parent_links,
    _add_previous_and_next_links,
    _get_by_type,
)
from mkdocs.structure.pages import Page
from mkdocs.utils import get_relative_url

MARKER = "<!-- family-tree -->"
SPOUSE = "💍"  # значок супруга в древе и в меню
OTHER_BRANCH = "Другие"  # вкладка для корней без `tree_branch`
FILE_ID = re.compile(r"^(P\d{4})-")
H1 = re.compile(r"^#\s+(.+?)\s*$", re.M)
YEARS = re.compile(r"^(.*\S)\s+\(([^()]*[\d?][^()]*)\)$")

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


def on_files(files, config):
    _people.clear()
    for f in files.documentation_pages():
        m = FILE_ID.match(posixpath.basename(f.src_uri))
        if not m or not f.src_uri.startswith("people/"):
            continue
        meta, body = _front_matter(f.content_string)
        if meta.get("hidden") or meta.get("in_tree") is False:
            continue
        h1 = H1.search(body)
        title = h1.group(1) if h1 else str(meta.get("name") or m.group(1))
        ym = YEARS.match(title)
        name, years = (ym.group(1), ym.group(2)) if ym else (title, "")
        born = re.match(r"\d{4}", str(meta.get("birth_date") or ""))
        _people[m.group(1)] = {
            "file": f,
            "name": name,
            "years": years,
            "sort": (int(born.group(0)) if born else 9999, name),
            "female": meta.get("sex") == "f",
            "village": str(meta.get("village") or ""),
            "branch": str(meta.get("tree_branch") or ""),
            "first_parents": _ids(meta.get("parents")),
            "parents": set(_ids(meta.get("parents"))),
            "spouses": set(_ids(meta.get("spouses"))),
            "children": set(_ids(meta.get("children"))),
        }
    # Достраиваем обратные связи и выбрасываем ссылки на неизвестных/скрытых.
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


def _sorted(ids):
    return sorted(ids, key=lambda i: _people[i]["sort"])


def _rank(pid):
    """Кто из супругов без родителей становится корнем: у кого больше детей на сайте,
    при равенстве — муж (жена встаёт рядом с ним), затем старший."""
    p = _people[pid]
    return (-len(p["children"]), p["female"], p["sort"])


def _root_order(roots, partners):
    """Корни по году рождения; пара стоит на месте старшего из супругов."""
    def key(pid):
        return min([_people[pid]["sort"]] + [_people[s]["sort"] for s in partners(pid)])
    return sorted(roots, key=key)


def _link(pid, page):
    p = _people[pid]
    href = get_relative_url(p["file"].url, page.url)
    years = f' <span class="ftree-years">{html.escape(p["years"])}</span>' if p["years"] else ""
    place = f'<span class="ftree-place">{html.escape(p["village"])}</span>' if p["village"] else ""
    return f'<span class="ftree-person"><a href="{href}">{html.escape(p["name"])}</a>{years}{place}</span>'


def _node(pid, page, seen):
    p = _people[pid]
    head = _link(pid, page)
    for s in _sorted(p["spouses"]):
        head += f' <span class="ftree-spouse" title="в браке с">{SPOUSE} {_link(s, page)}</span>'
    kids = [c for c in _sorted(p["children"]) if c not in seen]
    if not kids:
        return f'<li class="ftree-leaf"><span class="ftree-head">{head}</span></li>'
    inner = "".join(_node(c, page, seen | {c}) for c in kids)
    return (
        f'<li><details><summary><span class="ftree-head">{head}</span>'
        f' <span class="ftree-count" title="детей на сайте">{len(kids)}</span></summary>'
        f'<ul>{inner}</ul></details></li>'
    )


def _roots():
    roots = []
    for pid in _sorted(_people):
        p = _people[pid]
        if p["parents"]:
            continue
        # Супруг из семьи, которая есть на сайте, — человек виден там.
        if any(_people[s]["parents"] for s in p["spouses"]):
            continue
        # Оба супруга без родителей — показываем пару один раз (см. _rank).
        partners = [s for s in p["spouses"] if not _people[s]["parents"]]
        if any(_rank(s) < _rank(pid) for s in partners):
            continue
        roots.append(pid)
    return _root_order(roots, lambda r: [s for s in _people[r]["spouses"] if not _people[s]["parents"]])


def _branch(root):
    """Вкладка древа для корня: поле `tree_branch` у него или у супруга без родителей."""
    for pid in [root] + _sorted(_people[root]["spouses"]):
        if _people[pid]["branch"]:
            return _people[pid]["branch"]
    return OTHER_BRANCH


def _tabs(groups, page):
    """Вкладки в разметке pymdownx.tabbed (alternate_style) — их оформляет тема Material."""
    n = len(groups)
    inputs = "".join(
        f'<input{" checked" if i == 0 else ""} id="__ftree_{i + 1}" name="__ftree" type="radio">'
        for i in range(n)
    )
    labels = "".join(
        f'<label for="__ftree_{i + 1}">{html.escape(name)}</label>' for i, name in enumerate(groups)
    )
    blocks = "".join(
        '<div class="tabbed-block"><ul>' + "".join(_node(r, page, {r}) for r in roots) + "</ul></div>"
        for roots in groups.values()
    )
    return (
        f'<div class="tabbed-set tabbed-alternate" data-tabs="1:{n}">{inputs}'
        f'<div class="tabbed-labels">{labels}</div>'
        f'<div class="tabbed-content">{blocks}</div></div>'
    )


def on_page_markdown(markdown, page, config, files):
    if MARKER not in markdown:
        return markdown
    by_branch = {}
    for r in _roots():
        by_branch.setdefault(_branch(r), []).append(r)
    # Вкладки по алфавиту, «Другие» — последней.
    groups = {b: by_branch[b] for b in sorted(by_branch, key=lambda b: (b == OTHER_BRANCH, b))}
    tree = (
        '<div class="ftree">\n'
        '<div class="ftree-controls">'
        '<button type="button" class="md-button" data-ftree="open">Развернуть всё</button> '
        '<button type="button" class="md-button" data-ftree="close">Свернуть всё</button>'
        "</div>\n"
        f"{_tabs(groups, page)}\n"
        "</div>"
    )
    return markdown.replace(MARKER, tree)


# ---------- Левое меню ----------

class _IndexPage(Page):
    """Страница-«обложка» раздела меню: имя ведёт на неё, стрелка раскрывает раздел."""

    is_index = True


def _homes():
    """Куда поставить каждого человека в меню: ID -> (ID «хозяина» | None, «💍»?)."""
    homes = {}
    for pid in _sorted(_people):
        p = _people[pid]
        parents = [x for x in p["first_parents"] if x in p["parents"]] + _sorted(p["parents"])
        if parents:
            homes[pid] = (parents[0], False)
    for pid in _sorted(_people):
        if pid in homes:
            continue
        p = _people[pid]
        # Без родителей на сайте: ставим рядом с супругом, если тот — в какой-то семье.
        # Если оба супруга без родителей, корнем будет тот, кого выбирает _rank,
        # второй встанет рядом с ним.
        target = next((s for s in _sorted(p["spouses"]) if _people[s]["parents"]), None)
        if target is None:
            target = next(
                (
                    s
                    for s in _sorted(p["spouses"])
                    if homes.get(s, (None,))[0] is None and _rank(s) < _rank(pid)
                ),
                None,
            )
        homes[pid] = (target, target is not None)
    return homes


def _label(pid, titles):
    if titles.get(pid):
        return titles[pid]
    p = _people[pid]
    year = p["sort"][0]
    return f"{year} {p['name']}" if year != 9999 else p["name"]


_menu_places = {}  # подпись страницы в меню -> место (поле `village`)


def _url(pid):
    return _people[pid]["file"].url


def _menu_item(pid, homes, titles, label, seen, host=None):
    page = _people[pid]["file"].page
    page.title = label
    if _people[pid]["village"]:
        _menu_places[label] = _people[pid]["village"]
    kids = []
    # У супруга, стоящего рядом с мужем/женой (host), не повторяем host и общих детей.
    for s in _sorted(_people[pid]["spouses"] - {host}):
        if homes.get(s) == (pid, True) and s not in seen:
            kids.append(_menu_item(s, homes, titles, f"{SPOUSE} {_people[s]['name']}", seen | {s}, pid))
        else:
            kids.append(Link(f"{SPOUSE} {_people[s]['name']}", _url(s)))
    shared = _people[host]["children"] if host else set()
    for c in _sorted(_people[pid]["children"] - shared):
        if homes.get(c, (None,))[0] == pid and c not in seen:
            kids.append(_menu_item(c, homes, titles, _label(c, titles), seen | {c}))
        else:
            kids.append(Link(f"↗ {_label(c, titles)}", _url(c)))
    if not kids:
        return page
    page.__class__ = _IndexPage
    return Section(label, [page] + kids)


def on_nav(nav, config, files):
    section = next(
        (i for i in nav.items if isinstance(i, Section) and any(
            isinstance(c, Page) and c.file.src_uri == "people/index.md" for c in i.children
        )),
        None,
    )
    if section is None or not _people:
        return nav
    _menu_places.clear()
    titles = {pid: p["file"].page.title for pid, p in _people.items() if p["file"].page}
    homes = _homes()
    roots = _root_order(
        [pid for pid in _people if homes[pid][0] is None],
        lambda r: [s for s, h in homes.items() if h == (r, True)],
    )
    index = next(c for c in section.children if isinstance(c, Page) and c.file.src_uri == "people/index.md")
    others = [
        c for c in section.children
        if c is not index and not (isinstance(c, Page) and FILE_ID.match(posixpath.basename(c.file.src_uri)))
    ]
    section.children = [index] + [_menu_item(r, homes, titles, _label(r, titles), {r}) for r in roots] + others

    for page in _get_by_type(nav.items, Page):
        page.parent = None
    nav.pages = _get_by_type(nav.items, Page)
    _add_previous_and_next_links(nav.pages)
    _add_parent_links(nav.items)
    return nav


def on_post_page(output, page, config):
    """Место под подписью человека в левом меню (мелкая строка внутри ссылки)."""
    for label, place in _menu_places.items():
        pat = re.compile(
            r'(class="md-nav__link[^"]*"[^>]*>\s*<span class="md-ellipsis">\s*' + re.escape(html.escape(label, quote=False)) + r")(\s*</span>)"
        )
        tag = f'<small class="nav-place">{html.escape(place)}</small>'
        output = pat.sub(lambda m: m.group(1) + tag + m.group(2), output)
    return output

