"""Статус проверки страницы: плашка под заголовком (h1).

Страница, в front matter которой стоит `verified: "ГГГГ-ММ-ДД"`, получает
зелёную плашку «…полностью проверены автором сайта» с датой проверки;
остальные — серую «…Ожидает проверки автором». Дата проверки хранится
в front matter, то есть в Git; список проверенного ведётся также
во внутреннем чек-листе documents_check_list.md.

Плашки нет на главной, родословной, методологии, терминологии, «О проекте»,
на страницах фамилий и мест (surnames/, places/) и на реестрах источников
и персон — она стоит только на страницах отдельных источников и биографий.
"""

import re

SKIP_DIRS = ("surnames/", "places/")
SKIP = {"index.md", "tree.md", "research-method.md", "investigations.md", "terminology.md", "about.md",
        "sources/index.md", "people/index.md"}

TEXT = ("Материалы этой страницы подготовлены с помощью ИИ-инструментов "
        "на основе архивных документов и таблиц")

ICON_OK = ('<svg viewBox="0 0 20 20" aria-hidden="true">'
           '<rect x="1" y="1" width="18" height="18" rx="3.5" fill="#3f9a3f"/>'
           '<path d="M5.8 10.3l2.7 2.7 5.7-5.9" fill="none" stroke="#fff" stroke-width="2" '
           'stroke-linecap="round" stroke-linejoin="round"/></svg>')
ICON_PENDING = ('<svg viewBox="0 0 20 20" aria-hidden="true">'
                '<circle cx="10" cy="10" r="8.2" fill="none" stroke="currentColor" stroke-width="1.6"/>'
                '<path d="M10 5.5V10l3 2" fill="none" stroke="currentColor" stroke-width="1.6" '
                'stroke-linecap="round"/></svg>')

H1_END = re.compile(r"</h1>", re.I)


def _badge(page):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(page.meta.get("verified", "")))
    if m:
        date = f"{m.group(3)}.{m.group(2)}.{m.group(1)}"
        return (f'<p class="vstatus vstatus--ok">{ICON_OK}'
                f'<span>{TEXT} и полностью проверены автором сайта. '
                f'Дата проверки: {date}.</span></p>')
    return (f'<p class="vstatus vstatus--pending">{ICON_PENDING}'
            f'<span>{TEXT}. Ожидает проверки автором.</span></p>')


def on_page_content(html, page, config, files):
    if page.file.src_uri in SKIP or page.file.src_uri.startswith(SKIP_DIRS):
        return html
    badge = _badge(page)
    m = H1_END.search(html)
    if m:
        return html[:m.end()] + "\n" + badge + html[m.end():]
    return badge + "\n" + html
