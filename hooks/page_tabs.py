"""Вкладки из разделов страницы.

На странице, где стоит строка `<!-- h2-tabs -->`, каждый раздел `## …` после
этой строки становится вкладкой: подпись — текст заголовка, содержимое — всё до
следующего `## `. Текст до первого `## ` остаётся над вкладками. Сам Markdown не
меняется (без отступов, как у pymdownx.tabbed), поэтому разделы можно править и
пополнять как обычно.

Разметка — как у pymdownx.tabbed (alternate_style), её оформляет тема Material;
ту же разметку строит хук родословного древа. Переход по ссылке с якорем
внутри скрытой вкладки открывает её — см. javascripts/page-tabs.js.
"""

import html
import re

MARKER = "<!-- h2-tabs -->"
H2 = re.compile(r"<h2[^>]*>(.*?)</h2>", re.S)
HEADERLINK = re.compile(r'<a class="headerlink"[^>]*>.*?</a>', re.S)


def on_page_content(content, page, config, files):
    if MARKER not in content:
        return content
    head, body = content.split(MARKER, 1)
    parts = H2.split(body)
    # parts: [до первого h2, заголовок1, текст1, заголовок2, текст2, …]
    before, pairs = parts[0], list(zip(parts[1::2], parts[2::2]))
    if not pairs:
        return head + body
    labels = [html.unescape(re.sub(r"<[^>]+>", "", HEADERLINK.sub("", t))).strip() for t, _ in pairs]
    inputs = "".join(
        f'<input{" checked" if i == 0 else ""} id="__ptabs_{i + 1}" name="__ptabs" type="radio">'
        for i in range(len(pairs))
    )
    label_html = "".join(
        f'<label for="__ptabs_{i + 1}">{html.escape(name)}</label>' for i, name in enumerate(labels)
    )
    blocks = "".join(f'<div class="tabbed-block">{text}</div>' for _, text in pairs)
    tabs = (
        f'<div class="tabbed-set tabbed-alternate page-tabs" data-tabs="1:{len(pairs)}">{inputs}'
        f'<div class="tabbed-labels">{label_html}</div>'
        f'<div class="tabbed-content">{blocks}</div></div>'
    )
    return head + before + tabs
