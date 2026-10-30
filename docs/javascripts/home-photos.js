// Карусель фото на главной: на телефоне — точки под лентой (листание — CSS scroll-snap).
(function () {
  var strip = document.querySelector(".home-photos");
  if (!strip) return;
  var items = strip.querySelectorAll("a");
  if (items.length < 2) return;

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

  function update() {
    var center = strip.scrollLeft + strip.clientWidth / 2;
    var best = 0, bestDist = Infinity;
    items.forEach(function (item, i) {
      var d = Math.abs(item.offsetLeft + item.offsetWidth / 2 - center);
      if (d < bestDist) { bestDist = d; best = i; }
    });
    dots.querySelectorAll("button").forEach(function (dot, i) {
      dot.setAttribute("aria-current", i === best ? "true" : "false");
    });
  }
  strip.addEventListener("scroll", update, { passive: true });
  window.addEventListener("resize", update);
  update();
})();
