"""Страницы мест (docs/places/): содержимое оборачивается в <div class="place-page">,
чтобы extra.css мог оформить их таблицы отдельно («серая бумага»)."""


def on_page_content(html, page, config, files):
    if page.file.src_uri.startswith("places/"):
        return f'<div class="place-page">\n{html}\n</div>'
    return html
