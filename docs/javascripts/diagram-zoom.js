// Кнопка «на весь экран» над схемами (mermaid и нарисованные вручную div.kin-scheme).
(function () {
  function button(text, title, onClick) {
    var b = document.createElement("button");
    b.type = "button"; b.textContent = text; b.title = title;
    b.setAttribute("aria-label", title);
    b.addEventListener("click", onClick);
    return b;
  }
  function setup(diagram) {
    if (diagram.dataset.zoom) return;
    diagram.dataset.zoom = "1";
    var wrap = document.createElement("div");
    wrap.className = "diagram-zoom";
    var bar = document.createElement("div");
    bar.className = "diagram-zoom__bar";
    var area = document.createElement("div");
    area.className = "diagram-zoom__area";
    diagram.parentNode.insertBefore(wrap, diagram);
    area.appendChild(diagram);
    wrap.appendChild(bar);
    wrap.appendChild(area);
    if (wrap.requestFullscreen) {
      bar.appendChild(button("⛶", "На весь экран", function () {
        if (document.fullscreenElement) document.exitFullscreen();
        else wrap.requestFullscreen();
      }));
    }
  }
  // Схема родни на странице персоны (div.kin-nav): у неё своя рамка, поэтому
  // кнопка встаёт в её заголовок, а на весь экран разворачивается сама схема.
  function setupKin(nav) {
    if (nav.dataset.zoom || !nav.requestFullscreen) return;
    nav.dataset.zoom = "1";
    var title = nav.querySelector(".kin-title");
    if (!title) return;
    var b = button("⛶", "На весь экран", function () {
      if (document.fullscreenElement) document.exitFullscreen();
      else nav.requestFullscreen();
    });
    b.className = "kin-zoom";
    title.appendChild(b);
  }
  function scan() {
    document.querySelectorAll("div.mermaid, div.kin-scheme").forEach(setup);
    document.querySelectorAll("div.kin-nav").forEach(setupKin);
  }
  new MutationObserver(scan).observe(document.body, { childList: true, subtree: true });
  scan();
})();
