// Reload-only form persistence. Saves every named form field (including
// island-rendered inputs) to sessionStorage; restores on reload-type loads.
// Svelte islands restore their own subtrees from the same payload (see
// frontend/lib/form-persist.ts) — the generic restore below skips them.
//
// Save listeners are always armed (a fresh navigate clears any stale
// payload first) so the FIRST reload already restores. Historically saving
// only armed on reload-type loads and restore hung off `alpine:initialized`,
// which had already fired before this script ran — restore was dead code.
(function () {
  "use strict";

  var navEntry = performance.getEntriesByType("navigation")[0];
  var navType = navEntry ? navEntry.type : "navigate";
  var STORAGE_KEY = "form_persist:" + location.pathname;

  // ── Save ────────────────────────────────────────────────────────────────

  function collectFields() {
    var data = {};
    document.querySelectorAll("form [name]").forEach(function (el) {
      if (el.type === "file") return;
      var name = el.name;
      if (el.tagName === "SELECT" && el.multiple) {
        data[name] = Array.from(el.selectedOptions).map(function (o) {
          return o.value;
        });
        return;
      }
      if (el.type === "checkbox" || el.type === "radio") {
        data[name] = el.checked;
        return;
      }
      if (!Array.isArray(data[name])) data[name] = [];
      data[name].push(el.value);
    });
    return data;
  }

  function save() {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(collectFields()));
  }

  // Debounce: input + change both fire rapidly; serialize at most every 300ms.
  var saveTimer = null;
  function scheduleSave() {
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(save, 300);
  }

  document.addEventListener("input", scheduleSave);
  document.addEventListener("change", scheduleSave);
  // Flush any pending save before navigating away so nothing is lost.
  window.addEventListener("beforeunload", function () {
    if (saveTimer) clearTimeout(saveTimer);
    save();
  });

  // ── Restore (reload loads only) ─────────────────────────────────────────

  if (navType !== "reload") {
    sessionStorage.removeItem(STORAGE_KEY);
    return;
  }

  var rawStored = sessionStorage.getItem(STORAGE_KEY);
  if (!rawStored) return;

  var data;
  try {
    data = JSON.parse(rawStored);
  } catch {
    return;
  }

  // Deferred scripts run with the DOM parsed — restore immediately.
  var seen = {};
  document.querySelectorAll("form [name]").forEach(function (el) {
    if (el.type === "file") return;
    // Svelte islands restore their own inputs from the same payload.
    if (el.closest("[data-island]")) return;

    var name = el.name;
    var storedVal = data[name];
    if (storedVal === undefined) return;

    if (el.tagName === "SELECT" && el.multiple) {
      var multiValues = Array.isArray(storedVal) ? storedVal : [storedVal];
      Array.from(el.options).forEach(function (opt) {
        opt.selected = multiValues.includes(opt.value);
      });
      el.dispatchEvent(new Event("change", { bubbles: true }));
      return;
    }

    if (el.type === "checkbox" || el.type === "radio") {
      el.checked = storedVal;
      el.dispatchEvent(new Event("change", { bubbles: true }));
      return;
    }

    if (!seen[name]) seen[name] = 0;
    var idx = seen[name]++;
    var values = Array.isArray(storedVal) ? storedVal : [storedVal];
    if (idx < values.length) {
      el.value = values[idx];
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
    }
  });
})();
