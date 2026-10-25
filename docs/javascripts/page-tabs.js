// Вкладки из разделов страницы (хук page_tabs.py): если якорь в адресе
// ведёт внутрь скрытой вкладки, открыть её и прокрутить к цели.
(function () {
  function openTarget() {
    var id = decodeURIComponent(location.hash.slice(1));
    if (!id) return;
    var target = document.getElementById(id);
    if (!target) return;
    var block = target.closest(".page-tabs .tabbed-block");
    if (!block) return;
    var set = block.closest(".tabbed-set");
    var blocks = Array.prototype.slice.call(set.querySelectorAll(":scope > .tabbed-content > .tabbed-block"));
    var input = set.querySelectorAll(":scope > input")[blocks.indexOf(block)];
    if (input && !input.checked) {
      input.checked = true;
      input.dispatchEvent(new Event("change", { bubbles: true }));
    }
    target.scrollIntoView();
  }
  document.addEventListener("DOMContentLoaded", openTarget);
  window.addEventListener("hashchange", openTarget);
})();
