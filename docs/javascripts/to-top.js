// Плавающая кнопка «Наверх» в правом нижнем углу.
(function () {
  var btn = document.createElement("button");
  btn.className = "to-top";
  btn.type = "button";
  btn.title = "Наверх";
  btn.setAttribute("aria-label", "Наверх");
  btn.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M13 20h-2V8l-5.5 5.5-1.42-1.42L12 4.16l7.92 7.92-1.42 1.42L13 8v12z"/></svg>';
  btn.addEventListener("click", function () {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
  document.body.appendChild(btn);
  function update() {
    btn.classList.toggle("to-top--visible", window.scrollY > 400);
  }
  window.addEventListener("scroll", update, { passive: true });
  update();
})();
