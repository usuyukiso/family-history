// Кнопки «Развернуть всё» / «Свернуть всё» у родословного древа.
document.addEventListener("click", function (e) {
  var btn = e.target.closest(".ftree-controls [data-ftree]");
  if (!btn) return;
  var open = btn.getAttribute("data-ftree") === "open";
  btn.closest(".ftree").querySelectorAll("details").forEach(function (d) {
    d.open = open;
  });
});
