// Вкладки из разделов страницы (хук page_tabs.py):
// 1) если якорь в адресе ведёт внутрь скрытой вкладки, открыть её и прокрутить к цели;
// 2) в оглавлении справа показывать только пункты открытой вкладки
//    (у каждой вкладки свой список: буквы, века).
(function () {
  function blocksOf(set) {
    return Array.prototype.slice.call(set.querySelectorAll(":scope > .tabbed-content > .tabbed-block"));
  }

  function activeBlock(set) {
    var inputs = Array.prototype.slice.call(set.querySelectorAll(":scope > input"));
    for (var i = 0; i < inputs.length; i++) if (inputs[i].checked) return blocksOf(set)[i];
    return null;
  }

  function syncToc() {
    var links = document.querySelectorAll('.md-nav--secondary a.md-nav__link[href^="#"]');
    Array.prototype.forEach.call(links, function (link) {
      var target = document.getElementById(decodeURIComponent(link.getAttribute("href").slice(1)));
      var block = target && target.closest(".page-tabs .tabbed-block");
      if (!block) return;
      var item = link.closest(".md-nav__item");
      if (item) item.hidden = block !== activeBlock(block.closest(".tabbed-set"));
    });
  }

  function openTarget() {
    var id = decodeURIComponent(location.hash.slice(1));
    if (!id) return;
    var target = document.getElementById(id);
    if (!target) return;
    var block = target.closest(".page-tabs .tabbed-block");
    if (!block) return;
    var set = block.closest(".tabbed-set");
    var input = set.querySelectorAll(":scope > input")[blocksOf(set).indexOf(block)];
    if (input && !input.checked) {
      input.checked = true;
      input.dispatchEvent(new Event("change", { bubbles: true }));
    }
    target.scrollIntoView();
  }

  document.addEventListener("DOMContentLoaded", function () {
    openTarget();
    syncToc();
    Array.prototype.forEach.call(document.querySelectorAll(".page-tabs > input"), function (input) {
      input.addEventListener("change", syncToc);
    });
  });
  window.addEventListener("hashchange", openTarget);
})();
