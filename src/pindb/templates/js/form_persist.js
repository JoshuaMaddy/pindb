(function () {
  "use strict";

  var navEntry = performance.getEntriesByType("navigation")[0];
  var navType = navEntry ? navEntry.type : "navigate";
  var STORAGE_KEY = "form_persist:" + location.pathname;

  if (navType !== "reload") {
    sessionStorage.removeItem(STORAGE_KEY);
    return;
  }

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

  document.addEventListener("input", save);
  document.addEventListener("change", save);

  // ── Restore ─────────────────────────────────────────────────────────────

  var rawStored = sessionStorage.getItem(STORAGE_KEY);
  if (!rawStored) return;

  var data;
  try {
    data = JSON.parse(rawStored);
  } catch {
    return;
  }

  document.addEventListener("alpine:initialized", function () {
    // Restore Alpine x-data components (links, grades)
    document.querySelectorAll("[x-data]").forEach(function (el) {
      if (!window.Alpine) return;
      try {
        var alpine = Alpine.$data(el);

        if (Array.isArray(alpine.links) && Array.isArray(data.links) && data.links.length) {
          alpine.links = data.links.slice();
        }

        if (Array.isArray(alpine.grades)) {
          var names = data.grade_names;
          var prices = data.grade_prices;
          if (Array.isArray(names) && names.length) {
            alpine.grades = names.map(function (gradeName, i) {
              return {
                id: crypto.randomUUID(),
                name: gradeName,
                price: prices && prices[i] != null ? prices[i] : "",
              };
            });
          }
        }
      } catch {}
    });

    // Restore non-Alpine form fields
    var seen = {};
    document.querySelectorAll("form [name]").forEach(function (el) {
      if (el.type === "file") return;
      // Alpine x-model inputs are handled above via $data — skip here
      if (el.closest("[x-data]") && el.hasAttribute("x-model")) return;

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
  });
})();
