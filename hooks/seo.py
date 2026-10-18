"""Поисковики: описание страниц, закрытие от индекса, даты в sitemap.

- **Описание.** Если в front matter нет `description:`, оно собирается из
  первого абзаца текста страницы (без ссылок, ID источников и разметки),
  до ~160 знаков; у источников перед ним — название (`title`),
  у населённых пунктов — `name`, если его нет в абзаце. Material выводит его в `<meta name="description">`.
- **Закрытие от индекса** (`<meta name="robots" content="noindex">` и удаление
  из sitemap; на самом сайте страница остаётся в меню и в поиске):
  - персоны, родившиеся в 1900 г. и позже (`birth_date`);
  - источники, датированные 1918 г. и позже (`document_date`);
  - любая страница с `noindex: true`; `noindex: false` отменяет правило.
- **Даты в sitemap.** `<lastmod>` — дата последнего коммита, менявшего .md-файл
  страницы (а не дата сборки). Файлы вне git получают дату сборки.

robots.txt не создаётся: сайт лежит в подкаталоге (/family-history/), а
поисковики читают robots.txt только из корня домена. Sitemap добавляется
вручную в Google Search Console / Яндекс.Вебмастере.
"""

import gzip
import html
import logging
import os
import re
import subprocess

log = logging.getLogger("mkdocs.hooks.seo")

PERSON_FROM = 1900
SOURCE_FROM = 1918
MAX_LEN = 160

_noindex = set()  # url страницы
_lastmod = {}  # url -> YYYY-MM-DD
_git_dates = None  # путь .md относительно docs/ -> YYYY-MM-DD


def _year(value):
    m = re.match(r"\s*(\d{4})", str(value or ""))
    return int(m.group(1)) if m else None


def _is_noindex(page):
    meta = page.meta
    if "noindex" in meta:
        return bool(meta["noindex"])
    src = page.file.src_uri
    if src.startswith("people/"):
        y = _year(meta.get("birth_date"))
        return y is not None and y >= PERSON_FROM
    if src.startswith("sources/"):
        y = _year(meta.get("document_date"))
        return y is not None and y >= SOURCE_FROM
    return False


def _plain(text):
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)  # картинки
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)  # ссылки → текст
    text = re.sub(r"\s*\[\^?[A-Z]{1,3}\d{4}[^\]]*\]", "", text)  # [A1206], [^1]
    text = re.sub(r"\s*\[\^[^\]]+\]", "", text)
    text = re.sub(r"\{[:.#][^}]*\}", "", text)  # attr_list
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[*_`]+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _first_paragraph(markdown):
    para = []
    in_fence = False
    for line in markdown.splitlines():
        s = line.strip()
        if s.startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not s:
            if para:
                break
            continue
        if para:
            para.append(s)
            continue
        if s.startswith(("#", "|", "<", "!!!", "???", "- ", "* ", ">", "{", "[^")) or re.match(r"\d+\.", s):
            continue
        para.append(s)
    text = _plain(" ".join(para))
    return re.sub(r"^Полное описание:\s*", "", text)


def _shorten(text):
    if len(text) <= MAX_LEN:
        return text
    cut = text[:MAX_LEN].rsplit(" ", 1)[0].rstrip(",;:.—– ")
    return cut + "…"


def _load_git_dates(docs_dir):
    dates = {}
    try:
        out = subprocess.run(
            ["git", "log", "--format=@%cs", "--name-only", "--", "."],
            cwd=docs_dir, capture_output=True, text=True, check=True,
        ).stdout
        top = subprocess.run(
            ["git", "rev-parse", "--show-prefix"],
            cwd=docs_dir, capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        log.warning("git недоступен: в sitemap будет дата сборки")
        return dates
    date = None
    for line in out.splitlines():
        if line.startswith("@"):
            date = line[1:]
        elif line and date and line.startswith(top):
            dates.setdefault(line[len(top):], date)  # первая встреча = последний коммит
    return dates


def on_pre_build(config):
    global _git_dates
    _noindex.clear()
    _lastmod.clear()
    _git_dates = _load_git_dates(config["docs_dir"])


def on_page_markdown(markdown, page, config, files):
    if not page.meta.get("description"):
        desc = _first_paragraph(markdown)
        title = page.meta.get("title")
        if page.file.src_uri.startswith("sources/") and title:
            desc = f"{_plain(str(title))}. {desc}"  # у листов одного дела первый абзац общий
        name = page.meta.get("name")
        if page.file.src_uri.startswith("places/") and name and name not in desc:
            desc = f"{name}. {desc}"
        desc = _shorten(desc)
        if desc:
            page.meta["description"] = html.escape(desc)
    if _is_noindex(page) and not page.meta.get("hidden"):
        _noindex.add(page.url)
    date = _git_dates.get(page.file.src_uri) if _git_dates else None
    if date:
        _lastmod[page.url] = date
    return markdown


def on_post_page(output, page, config):
    if page.url in _noindex:
        output = output.replace("<head>", '<head>\n<meta name="robots" content="noindex">', 1)
    return output


def on_post_build(config):
    site = config["site_dir"]
    base = config["site_url"] or ""
    path = os.path.join(site, "sitemap.xml")
    if os.path.exists(path):
        xml = open(path, encoding="utf-8").read()

        def fix(m):
            url = m.group(1)[len(base):] if m.group(1).startswith(base) else m.group(1)
            if url in _noindex:
                return ""
            block = m.group(0)
            if url in _lastmod:
                block = re.sub(r"<lastmod>[^<]*</lastmod>", f"<lastmod>{_lastmod[url]}</lastmod>", block)
            return block

        xml = re.sub(r"\s*<url>\s*<loc>([^<]*)</loc>.*?</url>", fix, xml, flags=re.S)
        open(path, "w", encoding="utf-8").write(xml)
        with gzip.open(path + ".gz", "wb") as fh:
            fh.write(xml.encode("utf-8"))
