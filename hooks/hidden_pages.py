"""Скрытые страницы: доступны только по прямой ссылке.

Страница скрыта, если в её front matter стоит `hidden: true`. Хук:
- исключает её из поиска (как `search: exclude: true`);
- добавляет в <head> `<meta name="robots" content="noindex, nofollow">`;
- убирает её из sitemap.xml и sitemap.xml.gz;
- предупреждает (а `mkdocs build --strict` падает), если на скрытую страницу
  ссылается другая страница — по ID («[P1004]», «](P1004)») или по имени файла.

В меню (`nav`) скрытую страницу не добавляют; чтобы MkDocs не сообщал об этом,
она перечислена в `not_in_nav` в mkdocs.yml.
"""

import gzip
import logging
import os
import posixpath
import re

log = logging.getLogger("mkdocs.hooks.hidden_pages")

FILE_ID = re.compile(r"^([A-Z]{1,3}\d{4})-")
_hidden = {}  # src_uri -> (ID или None, url)


def on_page_markdown(markdown, page, config, files):
    if page.meta.get("hidden"):
        page.meta.setdefault("search", {})["exclude"] = True
        name = posixpath.basename(page.file.src_uri)
        m = FILE_ID.match(name)
        _hidden[page.file.src_uri] = (m.group(1) if m else None, page.url)
    return markdown


def on_post_page(output, page, config):
    if page.meta.get("hidden"):
        output = output.replace(
            "<head>", '<head>\n<meta name="robots" content="noindex, nofollow">', 1
        )
    return output


def on_env(env, config, files):
    # К этому моменту все страницы прочитаны: ищем ссылки на скрытые.
    for f in files.documentation_pages():
        page = f.page
        if page is None or page.meta.get("hidden") or page.markdown is None:
            continue
        for src, (pid, _url) in _hidden.items():
            base = posixpath.basename(src)
            if (pid and re.search(rf"[\[(]{pid}[\])]", page.markdown)) or base in page.markdown:
                log.warning("%s ссылается на скрытую страницу %s", f.src_uri, src)
    return env


def on_post_build(config):
    if not _hidden:
        return
    site = config["site_dir"]
    path = os.path.join(site, "sitemap.xml")
    if not os.path.exists(path):
        return
    xml = open(path, encoding="utf-8").read()
    for _pid, url in _hidden.values():
        xml = re.sub(
            rf"\s*<url>\s*<loc>[^<]*/{re.escape(url)}</loc>.*?</url>", "", xml, flags=re.S
        )
    open(path, "w", encoding="utf-8").write(xml)
    gz = path + ".gz"
    if os.path.exists(gz):
        with gzip.open(gz, "wb") as fh:
            fh.write(xml.encode("utf-8"))
