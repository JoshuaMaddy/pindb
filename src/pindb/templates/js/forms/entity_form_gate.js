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

  var FIELD_ORDER = cfg.fields.map(function (f) {
    return f.key;
  });
  var HINT_TEXT = {};
  cfg.fields.forEach(function (f) {
    HINT_TEXT[f.key] = f.hint;
  });

  var ERR_CLASSES = [
    "ring-2",
    "ring-error-main",
    "rounded-md",
    "border",
    "border-error-main",
    "p-1",
  ];

  var hintsShown = false;

  function tomSelectHasItems(selectId) {
    var el = document.getElementById(selectId);
    if (!el || !el.tomselect) return false;
    var v = el.tomselect.getValue();
    if (Array.isArray(v)) return v.length > 0;
    return v !== "" && v !== null && typeof v !== "undefined";
  }

  function buildChecks() {
    var checks = {};
    cfg.fields.forEach(function (f) {
      if (f.kind === "text") {
        checks[f.key] = function () {
          var el = document.getElementById(f.inputId);
          return !!(el && el.value.trim());
        };
      } else if (f.kind === "tomselect") {
        checks[f.key] = function () {
          return tomSelectHasItems(f.selectId);
        };
      }
    });
    return checks;
  }

  var checks = buildChecks();

  function computeValid() {
    return FIELD_ORDER.every(function (k) {
      return checks[k]();
    });
  }

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

  function removeHints() {
    document.querySelectorAll(".entity-form-field-hint").forEach(function (n) {
      n.remove();
    });
  }

  function clearErrorDecorations() {
    removeHints();
    FIELD_ORDER.forEach(function (key) {
      var el = findHighlightEl(key);
      if (!el) return;
      ERR_CLASSES.forEach(function (c) {
        el.classList.remove(c);
      });
    });
  }

  function applyHintsForInvalid() {
    clearErrorDecorations();
    FIELD_ORDER.forEach(function (key) {
      if (checks[key]()) return;
      var target = findHighlightEl(key);
      if (!target) return;
      ERR_CLASSES.forEach(function (c) {
        target.classList.add(c);
      });
      var hint = document.createElement("p");
      hint.className = "entity-form-field-hint text-error-main text-sm mt-1";
      hint.setAttribute("role", "alert");
      hint.textContent = HINT_TEXT[key];
      target.insertAdjacentElement("afterend", hint);
    });
  }

  function updateSubmitAppearance() {
    var ok = computeValid();
    submitBtn.classList.toggle("opacity-40", !ok);
    submitBtn.classList.toggle("cursor-not-allowed", !ok);
    submitBtn.setAttribute("aria-disabled", ok ? "false" : "true");
    submitBtn.title = ok ? "" : "Fill required fields to submit";
  }

  function refreshAfterHintsGate() {
    if (computeValid()) {
      hintsShown = false;
    }
    updateSubmitAppearance();
    if (!hintsShown) {
      clearErrorDecorations();
      return;
    }
    applyHintsForInvalid();
  }

  function scrollToFirstInvalid() {
    for (var i = 0; i < FIELD_ORDER.length; i++) {
      var key = FIELD_ORDER[i];
      if (checks[key]()) continue;
      var el = findHighlightEl(key);
      if (el && el.scrollIntoView) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
      }
      break;
    }
  }

  form.addEventListener(
    "submit",
    function (e) {
      if (computeValid()) {
        hintsShown = false;
        clearErrorDecorations();
        return;
      }
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      hintsShown = true;
      applyHintsForInvalid();
      updateSubmitAppearance();
      scrollToFirstInvalid();
    },
    true,
  );

  form.addEventListener("input", function () {
    refreshAfterHintsGate();
  });

  form.addEventListener(
    "change",
    function () {
      refreshAfterHintsGate();
    },
    true,
  );

  cfg.fields.forEach(function (f) {
    if (f.kind !== "tomselect") return;
    var el = document.getElementById(f.selectId);
    if (el && el.tomselect) {
      el.tomselect.on("change", refreshAfterHintsGate);
    }
  });

  updateSubmitAppearance();
}
