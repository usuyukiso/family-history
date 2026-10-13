"""Страницы источников XVIII века и старше (document_date до 1800 г.):
содержимое оборачивается в <div class="doc-18c">, чтобы extra.css показал
цитаты и расшифровки на «сильно состаренной» бумаге. Остальные документы
оформляются обычной бумагой без обёртки."""

import re


def on_page_content(html, page, config, files):
    if not page.file.src_uri.startswith("sources/"):
        return html
    m = re.match(r"\s*(\d{4})", str(page.meta.get("document_date", "")))
    if m and int(m.group(1)) < 1800:
        return f'<div class="doc-18c">\n{html}\n</div>'
    return html
