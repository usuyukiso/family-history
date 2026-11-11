// Кнопки «Развернуть всё» / «Свернуть всё» у родословного древа.
document.addEventListener("click", function (e) {
  var btn = e.target.closest(".ftree-controls [data-ftree]");
  if (!btn) return;
  var open = btn.getAttribute("data-ftree") === "open";
  btn.closest(".ftree").querySelectorAll("details:not(.ftree-single)").forEach(function (d) {
    d.open = open;
  });
});

// Корень без детей (details.ftree-single) не раскрывается; ссылки в нём работают.
document.addEventListener("click", function (e) {
  var summary = e.target.closest(".ftree details.ftree-single > summary");
  if (summary && !e.target.closest("a")) e.preventDefault();
});
