// «Что нового» (misc/changelog.md): вместо списка дат в правой колонке — календарь.
// Даты берутся из заголовков h2 вида «11 ноября 2026»; дни с новостями выделены,
// по щелчку страница прокручивается к записи. На узком экране, где правой
// колонки нет, календарь стоит над первой записью.
(function () {
  var GEN = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
             "августа", "сентября", "октября", "ноября", "декабря"];
  var NOM = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль",
             "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"];
  var WD = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"];

  function key(y, m, d) { return y + "-" + m + "-" + d; }

  function init() {
    if (!/\/misc\/changelog\/?$/.test(location.pathname.replace(/index\.html$/, ""))) return;
    var article = document.querySelector(".md-content__inner");
    if (!article) return;

    var days = {};      // "2026-10-11" -> h2
    var months = [];    // [год, месяц] с записями, по возрастанию
    article.querySelectorAll("h2[id]").forEach(function (h) {
      var m = h.textContent.trim().match(/^(\d{1,2})\s+([а-яё]+)\s+(\d{4})/i);
      if (!m) return;
      var mon = GEN.indexOf(m[2].toLowerCase());
      if (mon < 0) return;
      var y = +m[3], d = +m[1];
      days[key(y, mon, d)] = h;
      if (!months.some(function (x) { return x[0] === y && x[1] === mon; })) months.push([y, mon]);
    });
    if (!months.length) return;
    months.sort(function (a, b) { return a[0] - b[0] || a[1] - b[1]; });

    var cur = months.length - 1;
    var active = null;
    var box = document.createElement("div");
    box.className = "cl-cal";

    function render() {
      var y = months[cur][0], mon = months[cur][1];
      var first = (new Date(y, mon, 1).getDay() + 6) % 7;
      var total = new Date(y, mon + 1, 0).getDate();
      var html = '<div class="cl-cal__head">' +
        '<button type="button" class="cl-cal__nav" data-step="-1" aria-label="Предыдущий месяц"' +
        (cur === 0 ? " disabled" : "") + '>‹</button>' +
        '<span class="cl-cal__title">' + NOM[mon] + " " + y + "</span>" +
        '<button type="button" class="cl-cal__nav" data-step="1" aria-label="Следующий месяц"' +
        (cur === months.length - 1 ? " disabled" : "") + ">›</button></div>" +
        '<div class="cl-cal__grid">';
      WD.forEach(function (w, i) { html += '<span class="cl-cal__wd' + (i > 4 ? " cl-cal__wd--we" : "") + '">' + w + "</span>"; });
      for (var i = 0; i < first; i++) html += "<span></span>";
      var count = 0;
      for (var d = 1; d <= total; d++) {
        var h = days[key(y, mon, d)];
        if (h) {
          count++;
          html += '<a class="cl-cal__day cl-cal__day--has' + (active === h.id ? " is-active" : "") +
            '" href="#' + h.id + '" title="' + h.textContent.replace(/¶/g, "").trim() + '">' + d + "</a>";
        } else {
          html += '<span class="cl-cal__day">' + d + "</span>";
        }
      }
      html += "</div>";
      html += '<p class="cl-cal__note">' + count + " " + plural(count, ["день", "дня", "дней"]) +
        " с новостями</p>";
      box.innerHTML = html;
    }

    function plural(n, f) {
      var a = n % 10, b = n % 100;
      if (a === 1 && b !== 11) return f[0];
      if (a >= 2 && a <= 4 && (b < 12 || b > 14)) return f[1];
      return f[2];
    }

    box.addEventListener("click", function (e) {
      var btn = e.target.closest(".cl-cal__nav");
      if (btn && !btn.disabled) {
        cur += +btn.dataset.step;
        render();
      }
    });

    // Подсветка дня, запись которого сейчас на экране.
    var heads = Object.keys(days).map(function (k) { return days[k]; });
    function spy() {
      var top = null;
      heads.forEach(function (h) {
        if (h.getBoundingClientRect().top < 160 && (!top || h.getBoundingClientRect().top > top.getBoundingClientRect().top)) top = h;
      });
      if (!top) top = heads.reduce(function (a, b) { return a.getBoundingClientRect().top < b.getBoundingClientRect().top ? a : b; });
      if (top.id === active) return;
      active = top.id;
      var m = top.textContent.trim().match(/^(\d{1,2})\s+([а-яё]+)\s+(\d{4})/i);
      var idx = -1, y = +m[3], mon = GEN.indexOf(m[2].toLowerCase());
      months.forEach(function (x, i) { if (x[0] === y && x[1] === mon) idx = i; });
      if (idx >= 0) cur = idx;
      render();
    }

    // Место: правая колонка вместо оглавления или (узкий экран) над первой записью.
    var wide = window.matchMedia("(min-width: 60em)");
    var sidebar = document.querySelector(".md-sidebar--secondary .md-sidebar__inner");
    var firstH2 = heads[0];
    function place() {
      if (wide.matches && sidebar) {
        sidebar.innerHTML = "";
        sidebar.appendChild(box);
        box.classList.add("cl-cal--side");
      } else {
        firstH2.parentNode.insertBefore(box, firstH2);
        box.classList.remove("cl-cal--side");
      }
    }
    if (wide.addEventListener) wide.addEventListener("change", place);
    place();
    render();
    spy();
    window.addEventListener("scroll", function () { window.requestAnimationFrame(spy); }, { passive: true });
  }

  document.addEventListener("DOMContentLoaded", init);
})();
