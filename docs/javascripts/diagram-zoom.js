// Кнопка «на весь экран» над схемами (mermaid).
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
  function scan() { document.querySelectorAll("div.mermaid").forEach(setup); }
  new MutationObserver(scan).observe(document.body, { childList: true, subtree: true });
  scan();
})();
