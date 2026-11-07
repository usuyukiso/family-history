"""Название дела — бордовым (класс .delo-title в extra.css).

На страницах источников (docs/sources/…) в абзаце «**Полное описание:**»
первое название в кавычках «…», стоящее сразу после номера дела
(«д. 1590. «Исповедная роспись…»», «д. 432 — «Дѣло о ссудѣ…»»,
«д. 3260 «Метрические книги…»»), оборачивается в
<span class="delo-title">…</span>.

Выделяется только название, приведённое дословно в кавычках (с обложки
дела или из архивной описи). Пересказ составителя без кавычек не трогается.
Если на странице название уже обёрнуто вручную (<span class="delo-title">),
хук ничего не делает."""

import re

# «д. 1590.», «д. 755 (1745–1748).», «д. 432 —», «д. 3260 », «д. 326, л. 19. Дело называется»
DELO_TITLE = re.compile(
    r"(д\.\s*[0-9][0-9А-Яа-яA-Za-z/\-]*[^«\n]{0,45}?)(«[^»\n]{5,400}»)"
)


def on_page_markdown(markdown, page, config, files):
    if not page.file.src_uri.startswith("sources/"):
        return markdown
    if 'class="delo-title"' in markdown:
        return markdown
    lines = markdown.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("**Полное описание:**"):
            lines[i] = DELO_TITLE.sub(
                lambda m: f'{m.group(1)}<span class="delo-title">{m.group(2)}</span>',
                line,
                count=1,
            )
            break
    return "\n".join(lines)
