"""Таблицы дворов (исповедные росписи, ревизии): графы «Двор», «М.», «Ж.» —
только номера, поэтому таблица оборачивается в <div class="household-N">
(N — сколько первых граф номерные), и extra.css делает их узкими. Класс
ставится на обёртку, а не на <table>: стили завязаны на table:not([class])."""

import re

TABLE = re.compile(r"<table>\s*<thead>\s*<tr>(.*?)</tr>.*?</table>", re.S)
TH = re.compile(r"<th[^>]*>(.*?)</th>", re.S)
NUMERIC = {"Двор", "М.", "Ж."}


def _wrap(m):
    n = 0
    for head in TH.findall(m.group(1)):
        if head.strip() not in NUMERIC:
            break
        n += 1
    if not n or TH.findall(m.group(1))[0].strip() != "Двор":
        return m.group(0)
    return f'<div class="household-{n}">{m.group(0)}</div>'


def on_page_content(html, page, config, files):
    return TABLE.sub(_wrap, html)
