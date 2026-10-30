// Фото на главной.
// 1) Карусель: на телефоне — точки под лентой (листание — CSS scroll-snap).
// 2) Просмотр: по нажатию фото открывается на весь экран, листается свайпом,
//    стрелками и клавишами; закрывается крестиком, Esc, тапом по фону или «назад».
(function () {
  var strip = document.querySelector(".home-photos");
  if (!strip) return;
  var items = Array.prototype.slice.call(strip.querySelectorAll("a"));
  if (!items.length) return;

  // --- Точки под каруселью ---
  if (items.length > 1) {
    var dots = document.createElement("div");
    dots.className = "home-photos-dots";
    items.forEach(function (item, i) {
      var dot = document.createElement("button");
      dot.type = "button";
      dot.setAttribute("aria-label", "Фото " + (i + 1) + " из " + items.length);
      dot.addEventListener("click", function () {
        strip.scrollTo({
          left: item.offsetLeft - (strip.clientWidth - item.offsetWidth) / 2,
          behavior: "smooth"
        });
      });
      dots.appendChild(dot);
    });
    strip.after(dots);

    var updateDots = function () {
      var center = strip.scrollLeft + strip.clientWidth / 2;
      var best = 0, bestDist = Infinity;
      items.forEach(function (item, i) {
        var d = Math.abs(item.offsetLeft + item.offsetWidth / 2 - center);
        if (d < bestDist) { bestDist = d; best = i; }
      });
      dots.querySelectorAll("button").forEach(function (dot, i) {
        dot.setAttribute("aria-current", i === best ? "true" : "false");
      });
    };
    strip.addEventListener("scroll", updateDots, { passive: true });
    window.addEventListener("resize", updateDots);
    updateDots();
  }

  // --- Полноэкранный просмотр ---
  var box = document.createElement("div");
  box.className = "photo-lightbox";
  box.setAttribute("role", "dialog");
  box.setAttribute("aria-modal", "true");
  box.setAttribute("aria-label", "Просмотр фотографий");
  box.hidden = true;

  var track = document.createElement("div");
  track.className = "photo-lightbox__track";
  items.forEach(function (item) {
    var img = item.querySelector("img");
    var slide = document.createElement("figure");
    slide.className = "photo-lightbox__slide";
    var big = document.createElement("img");
    big.src = item.getAttribute("href");
    big.alt = img ? img.alt : "";
    big.loading = "lazy";
    slide.appendChild(big);
    if (big.alt) {
      var cap = document.createElement("figcaption");
      cap.textContent = big.alt;
      slide.appendChild(cap);
    }
    // Тап по фону вокруг фото закрывает просмотр
    slide.addEventListener("click", function (e) {
      if (e.target === slide) close();
    });
    track.appendChild(slide);
  });
  box.appendChild(track);

  function makeButton(cls, label, svgPath, onClick) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = "photo-lightbox__btn " + cls;
    b.setAttribute("aria-label", label);
    b.title = label;
    b.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="' + svgPath + '"/></svg>';
    b.addEventListener("click", onClick);
    box.appendChild(b);
    return b;
  }
  makeButton("photo-lightbox__close", "Закрыть",
    "M19 6.41 17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z",
    function () { close(); });
  var prevBtn = makeButton("photo-lightbox__prev", "Предыдущее фото",
    "M15.41 7.41 14 6l-6 6 6 6 1.41-1.41L10.83 12z", function () { go(current() - 1); });
  var nextBtn = makeButton("photo-lightbox__next", "Следующее фото",
    "M10 6 8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z", function () { go(current() + 1); });

  var counter = document.createElement("div");
  counter.className = "photo-lightbox__counter";
  box.appendChild(counter);

  document.body.appendChild(box);

  function current() {
    return Math.round(track.scrollLeft / track.clientWidth);
  }
  function go(i, instant) {
    i = Math.max(0, Math.min(items.length - 1, i));
    track.scrollTo({ left: i * track.clientWidth, behavior: instant ? "auto" : "smooth" });
  }
  function updateUi() {
    var i = current();
    counter.textContent = (i + 1) + " / " + items.length;
    prevBtn.disabled = i === 0;
    nextBtn.disabled = i === items.length - 1;
  }
  track.addEventListener("scroll", updateUi, { passive: true });

  var opened = false;
  function open(i) {
    opened = true;
    box.hidden = false;
    document.documentElement.classList.add("photo-lightbox-open");
    go(i, true);
    updateUi();
    // Кнопка «назад» на телефоне закрывает просмотр, а не уходит со страницы
    history.pushState({ photoLightbox: true }, "");
  }
  function hide() {
    opened = false;
    box.hidden = true;
    document.documentElement.classList.remove("photo-lightbox-open");
  }
  function close() {
    if (!opened) return;
    if (history.state && history.state.photoLightbox) history.back();
    else hide();
  }
  window.addEventListener("popstate", function () {
    if (opened) hide();
  });

  items.forEach(function (item, i) {
    item.addEventListener("click", function (e) {
      if (e.ctrlKey || e.metaKey || e.shiftKey || e.button !== 0) return;
      e.preventDefault();
      open(i);
    });
  });

  document.addEventListener("keydown", function (e) {
    if (!opened) return;
    if (e.key === "Escape") close();
    else if (e.key === "ArrowLeft") go(current() - 1);
    else if (e.key === "ArrowRight") go(current() + 1);
  });

  // При повороте экрана остаёмся на том же фото
  window.addEventListener("resize", function () {
    if (opened) go(Number(counter.textContent.split(" ")[0]) - 1, true);
  });
})();
