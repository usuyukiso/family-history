"""Раскрывающиеся разделы верхнего уровня в левом меню.

С `navigation.sections` Material показывает разделы верхнего уровня
(«Фамилии», «Источники» …) как заголовки, всегда раскрытые. Разделы из
COLLAPSIBLE вместо этого раскрываются по нажатию, как «Книги» внутри
«Источников»: у пункта меню снимается класс `md-nav__item--section`.
Правится готовый HTML (on_post_page), поэтому тема и nav не меняются.
"""

import re

# «Разное» теперь всегда раскрыто, как остальные разделы; список пуст, пока не понадобится снова.
COLLAPSIBLE = set()

_LI = re.compile(r'<li class="([^"]*\bmd-nav__item--section\b[^"]*)">')
_TITLE = re.compile(r'<span class="md-ellipsis">\s*([^<]*?)\s*</span>')


def on_post_page(output, page, config):
    out, pos = [], 0
    for m in _LI.finditer(output):
        t = _TITLE.search(output, m.end(), m.end() + 1500)
        if not t or t.group(1) not in COLLAPSIBLE:
            continue
        cls = re.sub(r"\s*\bmd-nav__item--section\b", "", m.group(1))
        out.append(output[pos:m.start()])
        out.append(f'<li class="{cls}">')
        pos = m.end()
        # заголовок раздела должен быть доступен с клавиатуры, как у вложенных пунктов
        lab = output.find('tabindex=""', pos, t.start())
        if lab != -1:
            out.append(output[pos:lab] + 'tabindex="0"')
            pos = lab + len('tabindex=""')
    out.append(output[pos:])
    return "".join(out)
