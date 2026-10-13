"""Ссылки по идентификаторам: [A1000], [P1000] и [текст](P1000).

Хук MkDocs. До сборки находит все страницы, имя файла которых начинается
с ID («A1000-…md», «P1000-…md»), и на каждой странице заменяет ссылки по ID
на обычные относительные Markdown-ссылки. Дальше MkDocs сам превращает их
в адреса сайта, поэтому base url в тексте не нужен.

  [A1000]            -> [A1000](../sources/archives/A1000-….md "название")  (код без скобок)
  [A1000][A1006]     -> те же ссылки через пробел: «A1000 A1006»
  [P1000]            -> [Евдокия Лапина](P1000-….md)  (для персон и мест PLC — имя)
  [текст](P1000)     -> [текст](P1000-….md)

Неизвестный ID даёт предупреждение; `mkdocs build --strict` на нём падает.
"""

import logging
import posixpath
import re

import yaml

log = logging.getLogger("mkdocs.hooks.id_links")

PREFIXES = "FAM|PLC|EV|DB|P|F|D|A|B|W|N|L|I|M|V|O"
FILE_ID = re.compile(rf"^((?:{PREFIXES})\d{{4}})-")
BARE = re.compile(rf"(?<!\w)\[((?:{PREFIXES})\d{{4}})\](?!\()")
ADJACENT = re.compile(rf"(\[(?:{PREFIXES})\d{{4}}\])(?=\[(?:{PREFIXES})\d{{4}}\](?!\())")
TARGET = re.compile(rf"\]\(((?:{PREFIXES})\d{{4}})\)")
FENCE = re.compile(r"^(```|~~~)")

_pages = {}  # ID -> (src_uri, подпись, всплывающая подсказка)


def _front_matter(text):
    if not text.startswith("---"):
        return {}
    try:
        return yaml.safe_load(text.split("---", 2)[1]) or {}
    except yaml.YAMLError:
        return {}


def on_files(files, config):
    _pages.clear()
    for f in files.documentation_pages():
        m = FILE_ID.match(posixpath.basename(f.src_uri))
        if not m:
            continue
        pid = m.group(1)
        if pid in _pages:
            log.warning("ID %s встречается дважды: %s и %s", pid, _pages[pid][0], f.src_uri)
        meta = _front_matter(f.content_string)
        title = str(meta.get("title") or meta.get("name") or pid)
        label = title if pid.startswith("P") else pid
        _pages[pid] = (f.src_uri, label, title)
    return files


def _rel(page, pid):
    if pid not in _pages:
        log.warning("%s: неизвестный ID %s", page.file.src_uri, pid)
        return None
    return posixpath.relpath(_pages[pid][0], posixpath.dirname(page.file.src_uri) or ".")


def on_page_markdown(markdown, page, config, files):
    def bare(m):
        pid = m.group(1)
        if not m.string[: m.start()].strip() and m.string[m.end() :].startswith(":"):
            return m.group(0)  # определение ссылки «[A1000]: …», не трогаем
        rel = _rel(page, pid)
        if rel is None:
            return m.group(0)
        _, label, title = _pages[pid]
        return f'[{label}]({rel} "{title.replace(chr(34), "")}")'

    def target(m):
        rel = _rel(page, m.group(1))
        return m.group(0) if rel is None else f"]({rel})"

    out, in_code = [], False
    for line in markdown.split("\n"):
        if FENCE.match(line.lstrip()):
            in_code = not in_code
        if not in_code:
            line = ADJACENT.sub(r"\1 ", line)
            line = TARGET.sub(target, BARE.sub(bare, line))
        out.append(line)
    return "\n".join(out)


def on_page_content(html, page, config, files):
    """На страницах персон и мест вставляет под заголовком краткое меню разделов (H2)."""
    if not FILE_ID.match(posixpath.basename(page.file.src_uri)) or not page.file.src_uri.startswith(("people/", "places/")):
        return html
    items = [c for top in page.toc for c in top.children] if page.toc else []
    if len(items) < 2:
        return html
    links = "".join(f'<li><a href="{i.url}">{i.title}</a></li>' for i in items)
    menu = f'<nav class="page-menu" aria-label="Разделы страницы"><ul>{links}</ul></nav>'
    pos = html.find("</h1>")
    return html[: pos + 5] + menu + html[pos + 5 :] if pos != -1 else menu + html
