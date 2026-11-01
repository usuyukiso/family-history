// Таблицы .bank-table (документы Крестьянского банка): текст вертикальных
// заголовков числовых граф оборачивается в <span class="vh">, чтобы его можно
// было поставить по центру над цифрами (сам повёрнутый <th> так не центрируется).
(function () {
  function wrap() {
    document.querySelectorAll(".bank-table table th").forEach(function (th) {
      var summary = th.closest(".bank-summary");
      var first = summary ? 2 : 3;
      if (th.cellIndex + 1 < first || th.querySelector(".vh")) return;
      var span = document.createElement("span");
      span.className = "vh";
      while (th.firstChild) span.appendChild(th.firstChild);
      th.appendChild(span);
      th.classList.add("vh-cell");
    });
  }
  document.addEventListener("DOMContentLoaded", wrap);
})();
