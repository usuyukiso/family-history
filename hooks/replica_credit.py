"""Страницы с копией бланка (поле `replica_skill: <имя скилла>` в front matter):
в конец страницы добавляется строка о том, каким скиллом из набора
genealogy-skills сделана копия, со ссылкой на папку скилла на GitHub."""

import html as _html

REPO = "https://github.com/usuyukiso/genealogy-skills"


def on_page_content(html, page, config, files):
    skill = str(page.meta.get("replica_skill", "")).strip()
    if not skill:
        return html
    name = _html.escape(skill)
    return (
        f"{html}\n"
        f'<p class="replica-credit">Копия бланка сгенерирована с помощью скилла '
        f'<a href="{REPO}/tree/main/{name}"><code>{name}</code></a> '
        f'из набора <a href="{REPO}">genealogy-skills на GitHub</a>.</p>\n'
    )
