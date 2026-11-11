/*
 * Поиск: короткий отрывок вместо всего текста раздела.
 *
 * Тема Material показывает в результате поиска весь текст найденного раздела — у длинных
 * страниц (биографии, источники) это экран-два текста, и до следующего результата долго
 * крутить. Здесь текст каждого результата заменяется отрывком вокруг первого найденного
 * слова (выделение <mark> сохраняется), с «…» по краям. Заголовок результата и ссылка не
 * меняются: по клику страница открывается как обычно, искомое слово на ней подсвечено.
 */
(function () {
  "use strict";

  var BEFORE = 70;    // символов до первого найденного слова
  var AFTER = 150;    // символов после него
  var MIN_LEN = BEFORE + AFTER + 40; // короче — оставляем как есть

  // Части статьи результата, которые не трогаем.
  function isKeep(el) {
    return el.tagName === "H1" || el.tagName === "H2" ||
      el.classList.contains("md-search-result__icon") ||
      el.classList.contains("md-search-result__terms") ||
      el.classList.contains("md-tags");
  }

  // Текст блоков в виде кусков {t: текст, m: выделено ли}; между блоками — пробел.
  function collect(nodes) {
    var parts = [];
    function walk(n) {
      if (n.nodeType === 3) { parts.push({ t: n.nodeValue, m: false }); return; }
      if (n.nodeType !== 1) return;
      if (n.tagName === "MARK") { parts.push({ t: n.textContent, m: true }); return; }
      var block = /^(P|LI|UL|OL|TR|TD|TH|TABLE|DIV|BLOCKQUOTE|PRE)$/.test(n.tagName);
      if (block) parts.push({ t: " ", m: false });
      for (var c = n.firstChild; c; c = c.nextSibling) walk(c);
      if (block) parts.push({ t: " ", m: false });
    }
    nodes.forEach(walk);
    // склеиваем пробелы
    var out = [], last = null;
    parts.forEach(function (p) {
      var t = p.t.replace(/\s+/g, " ");
      if (!t) return;
      if (last && last.m === p.m) { last.t += t; return; }
      last = { t: t, m: p.m }; out.push(last);
    });
    out.forEach(function (p) { p.t = p.t.replace(/ {2,}/g, " "); });
    if (out.length) out[0].t = out[0].t.replace(/^ /, "");
    return out;
  }

  function snip(article) {
    if (article.dataset.snip) return;
    article.dataset.snip = "1";
    // childNodes, а не children: Material часто кладёт текст раздела прямо в article,
    // без <p> (голые текстовые узлы между <mark>), — их тоже надо учесть и убрать.
    var body = Array.prototype.filter.call(article.childNodes, function (n) {
      return n.nodeType === 3 || (n.nodeType === 1 && !isKeep(n));
    });
    if (!body.length) return;
    var parts = collect(body);
    var total = parts.reduce(function (s, p) { return s + p.t.length; }, 0);
    if (total <= MIN_LEN) return;

    // позиция первого выделенного слова
    var pos = 0, first = -1;
    for (var i = 0; i < parts.length; i++) {
      if (parts[i].m) { first = pos; break; }
      pos += parts[i].t.length;
    }
    if (first < 0) first = 0;
    var from = Math.max(0, first - BEFORE), to = Math.min(total, first + AFTER);

    var p = document.createElement("p");
    p.className = "search-snippet";
    if (from > 0) p.appendChild(document.createTextNode("… "));
    pos = 0;
    parts.forEach(function (part) {
      var a = pos, b = pos + part.t.length;
      pos = b;
      var s = Math.max(a, from), e = Math.min(b, to);
      if (s >= e) return;
      var t = part.t.slice(s - a, e - a);
      if (part.m) { var m = document.createElement("mark"); m.textContent = t; p.appendChild(m); }
      else p.appendChild(document.createTextNode(t));
    });
    if (to < total) p.appendChild(document.createTextNode(" …"));

    body[0].parentNode.insertBefore(p, body[0]);
    body.forEach(function (el) { el.remove(); });
  }

  function run(root) {
    (root.querySelectorAll ? root : document)
      .querySelectorAll("article.md-search-result__article").forEach(snip);
  }

  new MutationObserver(function (records) {
    records.forEach(function (r) {
      r.addedNodes.forEach(function (n) {
        if (n.nodeType !== 1) return;
        if (n.matches && n.matches("article.md-search-result__article")) snip(n);
        else run(n);
      });
    });
  }).observe(document.documentElement, { childList: true, subtree: true });
})();
