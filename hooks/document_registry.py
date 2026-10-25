"""Реестр документов: данные для схемы docs/schemes/document-registry-tree.html.

Хук MkDocs. В схеме — только прямые предки (родители, деды, прадеды…) людей
из ROOTS и сами они; братья, сёстры, дети других веток в неё не попадают.
Живые родственники на сайте страниц не имеют; в схеме они — безымянные
узлы с одной буквой (STUBS), как на схеме «Семейные черты»; у них указано
только, какие документы есть у составителя.

Для каждого человека хук раскладывает его документы на четыре группы:
запись о рождении, запись о браке, запись о смерти и все остальные упоминания.
Сведения берутся со страниц сайта; вручную (COMPILER_DOCS) добавлены лишь
документы, которые есть у составителя, но на сайте не опубликованы:

- документы человека — поле `sources` его страницы и `related_people`
  страниц источников;
- вид записи — по названию источника («ч. 1 (о родившихся)», «брак»,
  «свидетельство о смерти», «учётная карточка воинского захоронения»…);
- запись считается записью о его собственном рождении (браке, смерти), если
  год документа сходится с годом события на странице человека и либо запись
  процитирована в строке «Родился» («Жена», «Умер»…) раздела «Краткие
  сведения», либо его имя стоит в названии записи. Так запись о рождении
  брата того же года не принимается за свою;
- почему родители — эти: строка «Отец» / «Мать» / «Родители» в «Кратких
  сведениях». Слова «по мнению составителя», «по-видимому», «по предположению»
  перед ссылкой на родителя — это вывод составителя; ссылки [A…] в строке —
  документы, по которым родство установлено.

Итог пишется в site/schemes/document-registry-data.js (window.REGISTRY),
схема подключает его обычным <script>.
"""

import json
import os
import posixpath
import re

import yaml
from mkdocs.utils import get_relative_url

# Чьи предки показываются (умершие люди с отдельной страницей).
ROOTS = ["P1109", "P1005", "P1006", "P1108"]
# Живые родственники — только связки в схеме: id, буква, родители,
# документы у составителя (вид события → название документа).
STUBS = [
    ["kids", "Ю, Д", ["pav", "oks"], {"birth": "свидетельства о рождении"}],
    ["pav", "П", ["P1109", "lar"], {"birth": "свидетельство о рождении", "marriage": "свидетельство о браке"}],
    ["lar", "Л", ["P1005", "P1006"], {"birth": "свидетельство о рождении",
                                      "marriage": ["два свидетельства о браке", "документ о расторжении первого брака"]}],
    ["oks", "О", ["yur", "P1108"], {"birth": "свидетельство о рождении", "marriage": "свидетельство о браке"}],
    ["yur", "Ю", [], {"birth": "свидетельство о рождении", "marriage": "свидетельство о браке"}],
]
# Документы, которые есть у составителя, но на сайте не опубликованы (со слов составителя,
# 2026-10-25). В схеме они считаются записью («зелёный»), в подсказке — «у составителя есть …».
COMPILER_DOCS = {
    "P1109": {"marriage": "свидетельство о браке"},  # свидетельство о смерти — на сайте, D1007
    "P1005": {"death": "свидетельство о смерти"},
    "P1108": {"birth": "свидетельство о рождении", "marriage": "свидетельство о браке",
              "death": "свидетельство о смерти",
              "other": ["паспорт", "партийный билет", "трудовая книжка",
                        "учётная карточка члена ВЛКСМ"]},
}
OUT = "schemes/document-registry-data.js"

FILE_ID = re.compile(r"^((?:P|A|B|D|DB|F|L|W)\d{4})-")
H1 = re.compile(r"^#\s+(.+?)\s*$", re.M)
YEARS = re.compile(r"^(.*\S)\s+\(([^()]*[\d?][^()]*)\)$")
CITE = re.compile(r"\[((?:A|B|D|DB|F|L|W)\d{4})\]")
LINK = re.compile(r"\[([^\]]*)\]\((?:\.\./)*(?:[\w/-]*/)?(P\d{4})[^)]*\)")
BULLET = re.compile(r"^- \*\*([^*]+?)\*\*(.*)$", re.M)
GUESS = re.compile(r"по мнению составителя|по-видимому|по предположению|предположительно|вероятно|возможно", re.I)
DATE = re.compile(r"\b\d{1,2}\.\d{2}\.\d{4}\b|\b\d{1,2}(?:/\d{1,2})? [а-я]+ \d{4}\b")
NOT_OWN = re.compile(r"восприемни|поручит|упом", re.I)

BIRTH_LABEL = re.compile(r"^(Родил(ся|ась)|Год рождения|Годы жизни)\b")
DEATH_LABEL = re.compile(r"^(Умер(ла)?|Погиб(ла)?|Годы жизни)\b")
# Отчества и фамилии («Афанасьев», «Никифорова», «Винник») не ищем в названии записи:
# «рождение Исаака, сына Сергея Афанасьева» — не запись о рождении отца.
NOT_GIVEN = re.compile(r"(ов|ев|ёв|ин|ова|ева|ёва|ина|ко|ич|вна|чна|ник|ский|ская|ой|ых)$")
SPOUSE_LABEL = re.compile(r"^((Первая |Вторая |Первый |Второй )?(Жена|Муж)|Жёны|Мужья)\b", re.I)
PARENT_LABEL = re.compile(r"^(Отец|Мать|Родители)\b", re.I)

_people = {}
_sources = {}


def _front_matter(text):
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    try:
        return yaml.safe_load(parts[1]) or {}, parts[2]
    except yaml.YAMLError:
        return {}, parts[2]


def _years(value):
    return [int(y) for y in re.findall(r"\d{4}", str(value or ""))]


def _kind(title):
    """Вид записи по названию источника: B — рождение, M — брак, D — смерть, O — прочее."""
    t = title.lower()
    if re.search(r"о родившихся|рождени|рожд\.|записей рождений", t):
        return "B"
    if re.search(r"бракосочет|брак|венча", t):
        return "M"
    if re.search(r"об умерших|смерт|захоронени|безвозвратных потерь", t):
        return "D"
    return "O"


def _short(sid):
    """«1754 — исповедная роспись»: год и вид документа, для пояснения о родстве."""
    s = _sources.get(sid)
    if not s:
        return sid
    t = s["title"]
    low = t.lower()
    year = re.match(r"\d{4}(?:[–-]\d{2,4})?", t)
    year = year.group(0) + " — " if year else ""
    for key, label in (("исповед", "исповедная роспись"), ("ревизск", "ревизская сказка"),
                       ("переписн", "переписная книга"), ("похозяйствен", "похозяйственная книга"),
                       ("алфавит", "алфавит"), ("свидетельство о рождении", "свидетельство о рождении")):
        if key in low:
            return year + label
    k = _kind(t)
    if k != "O":
        return year + {"B": "метрическая запись о рождении", "M": "запись о браке",
                       "D": "запись о смерти"}[k]
    rest = re.sub(r"^\d{4}(?:[–-]\d{2,4})?\s+", "", t)
    rest = rest.split(":")[-1].strip()
    return year + (rest[:60] + "…" if len(rest) > 60 else rest)


def _plain(md):
    """Строка «Кратких сведений» без разметки — для всплывающей подсказки."""
    t = LINK.sub(r"\1", re.sub(r"^-\s+", "", md))
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)
    t = CITE.sub("", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"\s+([,.;])", r"\1", re.sub(r"\s{2,}", " ", t)).strip(" ;")
    t = re.sub(r"\.\.(?!\.)", ".", t)
    return t if len(t) <= 260 else t[:257].rstrip() + "…"


def _summary(body):
    """Строки раздела «Краткие сведения» (до следующего заголовка ##)."""
    m = re.search(r"^## Краткие сведения\s*$(.*?)(?=^## |\Z)", body, re.M | re.S)
    part = m.group(1) if m else body
    return [(b.group(1).strip().rstrip(":").strip(), b.group(0)) for b in BULLET.finditer(part)]


def on_files(files, config):
    _people.clear()
    _sources.clear()
    for f in files.documentation_pages():
        m = FILE_ID.match(posixpath.basename(f.src_uri))
        if not m:
            continue
        meta, body = _front_matter(f.content_string)
        if f.src_uri.startswith("people/") and m.group(1).startswith("P"):
            h1 = H1.search(body)
            title = h1.group(1) if h1 else str(meta.get("name") or "")
            ym = YEARS.match(title)
            _people[m.group(1)] = {"file": f, "meta": meta, "body": body,
                                   "name": str(meta.get("name") or (ym.group(1) if ym else title)),
                                   "years": ym.group(2) if ym else ""}
        elif f.src_uri.startswith("sources/") and not meta.get("hidden"):
            title = str(meta.get("title") or m.group(1))
            year = (_years(meta.get("document_date")) or [None])[0]
            # «1860–1893 Метрические книги…» — несколько лет в одном источнике.
            span = re.match(r"(\d{4})[–-](\d{4})\s", title)
            _sources[m.group(1)] = {"file": f, "title": title, "year": year,
                                    "span": (int(span.group(1)), int(span.group(2))) if span else (year, year),
                                    "related": set(meta.get("related_people") or [])}
    return files


def _stems(p):
    """Начала личных имён человека («серг», «иоан»…) из `name` и `name_variants`."""
    names = [p["name"]] + [str(v) for v in p["meta"].get("name_variants") or []]
    out = set()
    for n in names:
        for w in re.findall(r"[А-ЯЁа-яё]+", n):
            w = w.lower()
            if len(w) >= 3 and not NOT_GIVEN.search(w):
                out.add(w[:4])
    return out


def _named(p, title):
    """Есть ли имя человека в названии записи (после двоеточия: «смерть Сергея Афанасьева»)."""
    tail = title.split(":", 1)[-1].lower()
    return any(re.search(r"(?<![а-яё])" + re.escape(s), tail) for s in _stems(p))


def _year_ok(y, years, before=0, after=0):
    return bool(years) and y is not None and min(years) - before <= y <= max(years) + after


def _person(pid, ids, url_of):
    p = _people[pid]
    meta, lines = p["meta"], _summary(p["body"])
    docs = set(meta.get("sources") or []) | {sid for sid, s in _sources.items() if pid in s["related"]}
    docs = sorted(d for d in docs if d in _sources)

    def bullets(rx):
        return [(lab, txt) for lab, txt in lines if rx.match(lab)]

    def cited(bl):
        return {c for _, txt in bl for c in CITE.findall(txt)}

    born, died = _years(meta.get("birth_date")), _years(meta.get("death_date"))
    exact_birth = len(set(born)) == 1 and meta.get("birth_date_status") == "confirmed"
    kids = [_years(_people[c]["meta"].get("birth_date")) for c in meta.get("children") or [] if c in _people]
    first_kid = min([k[0] for k in kids if k] or [None]) if any(kids) else None
    spouses = set(meta.get("spouses") or [])

    b_bl, d_bl, s_bl = bullets(BIRTH_LABEL), bullets(DEATH_LABEL), bullets(SPOUSE_LABEL)
    own = {"B": [], "M": [], "D": []}
    for sid in docs:
        s = _sources[sid]
        k = _kind(s["title"])
        if NOT_OWN.search(s["title"]):
            continue
        if k == "O":
            # Сборный источник («Метрические книги … 1860–1893»): его запись — та, ради
            # которой он процитирован в строке «Родился» / «Жена» / «Умер», если годы сходятся
            # и дата события точная (а не «ок. 1866 г. по записи о венчании»).
            if "метрическ" in s["title"].lower() and s["span"][0]:
                lo, hi = s["span"]
                def dated(bl):
                    return any(DATE.search(t) for _, t in bl if sid in t)
                for kk, bl, ev, exact in (
                        ("B", b_bl, born, meta.get("birth_date_status") == "confirmed" or dated(b_bl)),
                        ("M", s_bl, None, dated(s_bl)),
                        ("D", d_bl, died, meta.get("death_date_status") == "confirmed" or dated(d_bl))):
                    if exact and sid in cited(bl) and (ev is None or (ev and lo <= max(ev) and min(ev) <= hi)):
                        own[kk].append(sid)
            continue
        # Год события неизвестен — своей считается только запись, процитированная в его строке.
        y = s["year"]
        if k == "B":
            hit = (_year_ok(y, born, *(0, 0) if exact_birth else (1, 1))
                   and (sid in cited(b_bl) or _named(p, s["title"])))
        elif k == "D":
            hit = _year_ok(y, died, 0, 1) and (sid in cited(d_bl) or _named(p, s["title"]))
        else:
            adult = y is not None and (not born or y >= min(born) + 14)
            hit = adult and (sid in cited(s_bl) or (
                _named(p, s["title"]) and bool(spouses & s["related"])
                and (first_kid is None or y <= first_kid + 1)))
        if hit:
            own[k].append(sid)

    def doclist(sids):
        # Только ID; названия и адреса — один раз, в общем списке `sources`.
        return list(sids)

    # Родители и почему они — эти.
    parents = [q for q in meta.get("parents") or [] if q in ids]
    # Строка о родителе — в «Кратких сведениях», а если там её нет, то в любом разделе страницы.
    par_lines = bullets(PARENT_LABEL)
    all_par = [(b.group(1), b.group(0)) for b in BULLET.finditer(p["body"])
               if PARENT_LABEL.match(b.group(1).strip())]
    edges = {}
    for q in parents:
        seg_txt, cites, guess = "", [], False
        for _, txt in par_lines + all_par:
            if f"({q})" not in txt and not re.search(rf"\({q}[)#]", txt):
                continue
            segs = txt.split(";")
            seg = next(s for s in segs if re.search(rf"\b{q}\b", s))
            before = seg[:re.search(rf"\b{q}\b", seg).start()]
            guess = bool(GUESS.search(before))
            cites = CITE.findall(seg) or CITE.findall(txt)
            seg_txt = _plain(txt)
            break
        if guess:
            st = "guess"
        elif own["B"]:
            st = "rec"
        elif cites:
            st = "doc"
        else:
            st = "none"
        cites = [c for c in dict.fromkeys(cites) if c in _sources and c not in own["B"]]
        edges[q] = {"s": st, "text": seg_txt, "why": [_short(c) for c in cites], "docs": doclist(cites)}

    # Запись о рождении есть — зелёный, даже если о родителе есть оговорка (она видна на линии к нему).
    states = {e["s"] for e in edges.values()}
    if own["B"]:
        b_state = "rec"
    elif "guess" in states:
        b_state = "guess"
    elif "doc" in states:
        b_state = "doc"
    else:
        b_state = "none"

    def state(rec, bl, need_death=False):
        if rec:
            return "rec"
        if not cited(bl):
            return "none"
        if need_death:
            text = " ".join(txt for _, txt in bl)
            if not (died or re.search(r"умре|умер|умерл|похорон", text.split("**", 2)[-1], re.I)):
                return "none"
        return "doc"

    m_state = state(own["M"], s_bl)
    d_state = state(own["D"], d_bl, need_death=True)
    used = set(own["B"]) | set(own["M"]) | set(own["D"])
    other = [d for d in docs if d not in used]

    def info(bl):
        return [_plain(txt) for _, txt in bl][:2]

    out = {
        "id": pid, "name": p["name"], "years": p["years"], "sex": meta.get("sex"),
        "url": url_of(p["file"]), "parents": parents,
        "birth": {"s": b_state, "docs": doclist(own["B"]), "info": info(b_bl)},
        "marriage": {"s": m_state, "docs": doclist(own["M"]),
                     "info": info(s_bl), "cited": doclist([c for c in dict.fromkeys(cited(s_bl)) if c in _sources and c not in own["M"]])},
        "death": {"s": d_state, "docs": doclist(own["D"]),
                  "info": info(d_bl), "cited": doclist([c for c in dict.fromkeys(cited(d_bl)) if c in _sources and c not in own["D"]])},
        "other": {"docs": doclist(other)},  # + "held" из COMPILER_DOCS
        "edges": edges,
    }
    _add_held(out, COMPILER_DOCS.get(pid, {}))
    return out


def _add_held(entry, held):
    """Документы у составителя: событие «есть запись»; свидетельство о рождении
    подтверждает и родителей (кроме тех, что помечены как вывод составителя).
    Прочие документы (`other`) только добавляются к счёту и списку."""
    for key, title in held.items():
        entry[key]["held"] = title if isinstance(title, list) else [title]
        if key == "other":
            continue
        entry[key]["s"] = "rec"
        if key == "birth":
            for e in entry["edges"].values():
                if e["s"] != "guess":
                    e["s"] = "rec"


def _ancestors():
    out = []
    seen = set()
    stack = list(ROOTS)
    while stack:
        pid = stack.pop(0)
        if pid in seen or pid not in _people:
            continue
        meta = _people[pid]["meta"]
        if meta.get("hidden") or meta.get("living"):
            continue
        seen.add(pid)
        out.append(pid)
        stack.extend(meta.get("parents") or [])
    return out


def on_post_build(config):
    ids = set(_ancestors())
    page_url = posixpath.dirname(OUT) + "/"

    def url_of(f):
        return get_relative_url(f.url, page_url)

    people = {pid: _person(pid, ids, url_of) for pid in ids}
    used = set()
    for p in people.values():
        for key in ("birth", "marriage", "death", "other"):
            used.update(p[key]["docs"], p[key].get("cited", []))
        for e in p["edges"].values():
            used.update(e["docs"])
    sources = {sid: [_sources[sid]["title"], url_of(_sources[sid]["file"])] for sid in sorted(used)}
    stubs = []
    for sid, label, par, held in STUBS:
        empty = {"s": "none", "docs": [], "info": [], "cited": []}
        entry = {"id": sid, "label": label, "parents": par,
                 "birth": dict(empty), "marriage": dict(empty), "death": dict(empty),
                 "other": {"docs": []}, "edges": {q: {"s": "none", "text": "", "why": [], "docs": []} for q in par}}
        _add_held(entry, held)
        stubs.append(entry)
    data = {"people": people, "sources": sources, "stubs": stubs}
    path = os.path.join(config["site_dir"], OUT)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("window.REGISTRY=" + json.dumps(data, ensure_ascii=False) + ";\n")
