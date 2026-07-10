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
    } else if (f.kind === "select") {
      checks[f.key] = function () {
        return globalThis.pindbSelectHasItems(f.selectId);
      };
    }
  });

  function findHighlightEl(key) {
    var field = cfg.fields.find(function (ff) {
      return ff.key === key;
    });
    if (!field) return null;
    if (field.kind === "select") {
      var sel = document.getElementById(field.selectId);
      if (!sel) return null;
      return sel.closest("[data-multiselect]") || sel;
    }
    return document.querySelector(field.highlightSelector);
  }

  globalThis.pindbCreateFormGate({
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

  // Select widget islands dispatch bubbling change events on their adopted
  // selects; the gate's own form-level change listener picks those up.
}
