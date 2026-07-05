/**
 * Generic required-field gate + inline hints for simple create/edit forms
 * (shops, artists, tags, pin sets). Configuration JSON lives in
 * `#entity-form-gate-data`. Mirrors the UX pattern from `pins/pin_creation.js`.
 */
window.addEventListener("load", function () {
  var cfgEl = document.getElementById("entity-form-gate-data");
  if (!cfgEl || !cfgEl.textContent) return;
  var cfg;
  try {
    cfg = JSON.parse(cfgEl.textContent);
  } catch {
    return;
  }
  initEntityFormGate(cfg);
});

function initEntityFormGate(cfg) {
  var form = document.getElementById(cfg.formId);
  var submitBtn = document.getElementById(cfg.submitId);
  if (!form || !submitBtn || !cfg.fields || !cfg.fields.length) return;

  var fieldOrder = cfg.fields.map(function (f) {
    return f.key;
  });
  var hintText = {};
  var checks = {};
  cfg.fields.forEach(function (f) {
    hintText[f.key] = f.hint;
    if (f.kind === "text") {
      checks[f.key] = function () {
        var el = document.getElementById(f.inputId);
        return !!(el && el.value.trim());
      };
    } else if (f.kind === "tomselect") {
      checks[f.key] = function () {
        return globalThis.pindbTomSelectHasItems(f.selectId);
      };
    }
  });

  function findHighlightEl(key) {
    var field = cfg.fields.find(function (ff) {
      return ff.key === key;
    });
    if (!field) return null;
    if (field.kind === "tomselect") {
      var sel = document.getElementById(field.selectId);
      return sel && sel.tomselect ? sel.tomselect.wrapper : sel;
    }
    return document.querySelector(field.highlightSelector);
  }

  var gate = globalThis.pindbCreateFormGate({
    form: form,
    submitBtn: submitBtn,
    fieldOrder: fieldOrder,
    checks: checks,
    hintText: hintText,
    findHighlightEl: findHighlightEl,
    hintSelector: ".entity-form-field-hint",
    hintClassFor: function () {
      return "entity-form-field-hint text-error-main text-sm mt-1";
    },
  });

  // Tom Select changes don't bubble as form input/change — refresh manually.
  cfg.fields.forEach(function (f) {
    if (f.kind !== "tomselect") return;
    var el = document.getElementById(f.selectId);
    if (el && el.tomselect) {
      el.tomselect.on("change", gate.refresh);
    }
  });
}
