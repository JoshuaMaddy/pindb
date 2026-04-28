(function () {
  function syncThemeRadiosFromHtmlClass() {
    var root = document.documentElement;
    var cls = root.className || "";
    var theme = (cls.match(/^([^\s]+)/) || [undefined, "mocha"])[1];
    var form = document.getElementById("user-settings-form");
    if (!form) return;
    form.querySelectorAll('input[name="theme"]').forEach(function (inp) {
      inp.checked = inp.value === theme;
    });
  }
  function syncDimensionRadiosFromDataAttr() {
    var form = document.getElementById("user-settings-form");
    if (!form) return;
    var du = form.getAttribute("data-dimension-unit");
    if (!du) return;
    form.querySelectorAll('input[name="dimension_unit"]').forEach(function (inp) {
      inp.checked = inp.value === du;
    });
  }
  function onThemeRadioChange(ev) {
    var t = ev.target;
    if (!t || t.name !== "theme" || t.type !== "radio" || !t.checked) return;
    document.documentElement.className = t.value + " bg-darker";
  }
  function boot() {
    if (!document.getElementById("user-settings-form")) return;
    syncThemeRadiosFromHtmlClass();
    syncDimensionRadiosFromDataAttr();
    setTimeout(function () {
      document.body.addEventListener("change", onThemeRadioChange);
    }, 0);
  }
  if (document.readyState === "complete") {
    boot();
  } else {
    window.addEventListener("load", boot);
  }
})();
