// =============================================================================
// PinDB Bulk Tag Creation
//
// Spreadsheet-style row entry for tags. Each row has Name, Category,
// Implications (multi-select), Aliases (multi-select with create), and
// Description. Category changes broadcast to sibling rows' implication
// pickers so chips re-color reactively. Implication search merges DB hits
// (via /bulk/options/tag) with batch-local rows still being created.
//
// Reads window.BULK_TAG_REF (injected by templates/bulk/tag.py).
// =============================================================================

(function () {
  "use strict";

  const REF = window.BULK_TAG_REF;
  if (!REF) return;

  const tbody = document.getElementById("bulk-tag-tbody");
  const addRowBtn = document.getElementById("bulk-tag-add-row");
  const submitBtn = document.getElementById("bulk-tag-submit");

  // rowId -> { name, category, tomSelectInstances: { implications, aliases, category } }
  const rowRegistry = new Map();
  let rowCounter = 0;

  function uuid() {
    return (
      Math.random().toString(36).slice(2, 10) +
      "-" +
      Date.now().toString(36)
    );
  }

  function normalize(name) {
    return name.trim().toLowerCase().replace(/\s+/g, "_");
  }

  // ---------------------------------------------------------------------------
  // Cross-row broadcasting: when row A's category or name changes, every
  // OTHER row's implication picker must learn the new {value, text, category}.
  // ---------------------------------------------------------------------------
  function broadcastUpsert(currentRowId, item, oldValue) {
    rowRegistry.forEach(function (entry, rowId) {
      if (rowId === currentRowId) return;
      const ts = entry.tomSelectInstances.implications;
      if (!ts) return;
      if (oldValue && oldValue !== item.value && ts.options[oldValue]) {
        const wasSelected = ts.items.includes(oldValue);
        ts.removeOption(oldValue);
        if (wasSelected) {
          ts.addOption(item);
          ts.addItem(item.value, true);
        }
      }
      if (ts.options[item.value]) {
        ts.updateOption(item.value, Object.assign({}, ts.options[item.value], item));
      } else {
        ts.addOption(item);
      }
      if (ts.items.includes(item.value)) {
        ts.refreshItems();
      }
    });
  }

  function broadcastRemove(currentRowId, value) {
    if (!value) return;
    rowRegistry.forEach(function (entry, rowId) {
      if (rowId === currentRowId) return;
      const ts = entry.tomSelectInstances.implications;
      if (!ts) return;
      if (ts.items.includes(value)) ts.removeItem(value);
      if (ts.options[value]) ts.removeOption(value);
    });
  }

  // ---------------------------------------------------------------------------
  // Category select for a row
  // ---------------------------------------------------------------------------
  function buildCategorySelect(selectEl, rowId) {
    REF.categories.forEach(function (cat) {
      const opt = document.createElement("option");
      opt.value = cat.value;
      opt.textContent = cat.text;
      opt.dataset.icon = cat.icon;
      opt.dataset.color = cat.color;
      opt.dataset.category = cat.value;
      if (cat.value === "general") opt.selected = true;
      selectEl.appendChild(opt);
    });

    const TS = window.TomSelect;
    const tagSelectHelpers = (window.TagSelect &&
      window.TagSelect.tagSingleSelectCallbacks) || (() => ({}));
    const ts = new TS(selectEl, Object.assign(
      {
        valueField: "value",
        labelField: "text",
        searchField: ["text"],
        maxItems: 1,
        plugins: ["caret_position"],
        render: {
          option: window.TagSelect && window.TagSelect.tagOptionRender,
          item: window.TagSelect && window.TagSelect.tagItemRender,
        },
        onChange: function (value) {
          const entry = rowRegistry.get(rowId);
          if (!entry) return;
          entry.category = value;
          if (entry.name) {
            broadcastUpsert(rowId, {
              value: entry.name,
              text: entry.name,
              category: value,
            });
          }
        },
      },
      tagSelectHelpers()
    ));
    return ts;
  }

  // ---------------------------------------------------------------------------
  // Implication multi-select for a row. Loads DB hits + merges local rows.
  // ---------------------------------------------------------------------------
  function buildImplicationsSelect(selectEl, rowId) {
    const TS = window.TomSelect;
    const lucideHelpers = (window.TagSelect &&
      window.TagSelect.tagSelectLucideCallbacks) || (() => ({}));

    const ts = new TS(selectEl, Object.assign(
      {
        valueField: "value",
        labelField: "text",
        searchField: ["text"],
        maxItems: null,
        plugins: ["remove_button", "caret_position"],
        persist: false,
        dropdownParent: "body",
        shouldLoad: function (q) {
          return q.length >= 1;
        },
        load: function (query, callback) {
          const entry = rowRegistry.get(rowId);
          const selfName = entry && entry.name;
          const qs = new URLSearchParams({ q: query });
          if (selfName) qs.set("exclude_name", selfName);
          fetch(REF.optionsBaseUrl + "/tag?" + qs.toString())
            .then(function (r) { return r.json(); })
            .then(function (results) {
              // Merge local row entries (other rows) matching the query.
              const q = query.toLowerCase();
              rowRegistry.forEach(function (other, otherRowId) {
                if (otherRowId === rowId) return;
                if (!other.name) return;
                if (q && other.name.indexOf(q) === -1) return;
                if (results.find(function (r) { return r.value === other.name; })) return;
                results.push({
                  value: other.name,
                  text: other.name,
                  category: other.category || "general",
                });
              });
              callback(results);
            })
            .catch(function () { callback(); });
        },
        render: {
          option: window.TagSelect && window.TagSelect.tagOptionRender,
          item: window.TagSelect && window.TagSelect.tagItemRender,
        },
      },
      lucideHelpers()
    ));
    return ts;
  }

  // ---------------------------------------------------------------------------
  // Aliases multi-select with on-the-fly creation
  // ---------------------------------------------------------------------------
  function buildAliasesSelect(selectEl) {
    const TS = window.TomSelect;
    return new TS(selectEl, {
      valueField: "value",
      labelField: "text",
      maxItems: null,
      plugins: ["remove_button", "caret_position"],
      persist: false,
      create: function (input) {
        return { value: input, text: input };
      },
    });
  }

  // ---------------------------------------------------------------------------
  // Row construction
  // ---------------------------------------------------------------------------
  function makeRow() {
    rowCounter += 1;
    const rowId = "row-" + rowCounter;
    const tr = document.createElement("tr");
    tr.dataset.rowId = rowId;
    tr.dataset.clientId = uuid();
    tr.className = "border-b border-lightest";

    const nameTd = document.createElement("td");
    nameTd.className = "px-2 py-1";
    const nameInput = document.createElement("input");
    nameInput.type = "text";
    nameInput.required = true;
    nameInput.className = "w-full bg-transparent border border-lightest rounded px-1 py-0.5";
    nameInput.placeholder = "tag_name";
    nameTd.appendChild(nameInput);

    const categoryTd = document.createElement("td");
    categoryTd.className = "px-2 py-1";
    const categorySelect = document.createElement("select");
    categoryTd.appendChild(categorySelect);

    const implsTd = document.createElement("td");
    implsTd.className = "px-2 py-1";
    const implsSelect = document.createElement("select");
    implsSelect.multiple = true;
    implsTd.appendChild(implsSelect);

    const aliasesTd = document.createElement("td");
    aliasesTd.className = "px-2 py-1";
    const aliasesSelect = document.createElement("select");
    aliasesSelect.multiple = true;
    aliasesTd.appendChild(aliasesSelect);

    const descTd = document.createElement("td");
    descTd.className = "px-2 py-1";
    const descInput = document.createElement("textarea");
    descInput.rows = 1;
    descInput.className = "w-full bg-transparent border border-lightest rounded px-1 py-0.5";
    descTd.appendChild(descInput);

    const actionsTd = document.createElement("td");
    actionsTd.className = "px-2 py-1 flex gap-1";
    const dupBtn = document.createElement("button");
    dupBtn.type = "button";
    dupBtn.className = "text-xs px-2 py-0.5 border border-lightest rounded hover:border-accent";
    dupBtn.textContent = "Duplicate";
    const delBtn = document.createElement("button");
    delBtn.type = "button";
    delBtn.className = "text-xs px-2 py-0.5 border border-error-main rounded hover:bg-error-dark";
    delBtn.textContent = "Delete";
    actionsTd.appendChild(dupBtn);
    actionsTd.appendChild(delBtn);

    tr.appendChild(nameTd);
    tr.appendChild(categoryTd);
    tr.appendChild(implsTd);
    tr.appendChild(aliasesTd);
    tr.appendChild(descTd);
    tr.appendChild(actionsTd);

    tbody.appendChild(tr);

    rowRegistry.set(rowId, {
      name: "",
      category: "general",
      tomSelectInstances: {},
    });

    const tsCategory = buildCategorySelect(categorySelect, rowId);
    const tsImpls = buildImplicationsSelect(implsSelect, rowId);
    const tsAliases = buildAliasesSelect(aliasesSelect);
    rowRegistry.get(rowId).tomSelectInstances = {
      category: tsCategory,
      implications: tsImpls,
      aliases: tsAliases,
    };

    nameInput.addEventListener("input", function () {
      const entry = rowRegistry.get(rowId);
      if (!entry) return;
      const oldName = entry.name;
      const newName = normalize(nameInput.value);
      entry.name = newName;
      if (newName) {
        broadcastUpsert(
          rowId,
          { value: newName, text: newName, category: entry.category || "general" },
          oldName
        );
      } else if (oldName) {
        broadcastRemove(rowId, oldName);
      }
    });

    delBtn.addEventListener("click", function () {
      const entry = rowRegistry.get(rowId);
      if (entry) {
        Object.values(entry.tomSelectInstances).forEach(function (ts) {
          try { ts.destroy(); } catch (e) {}
        });
        if (entry.name) broadcastRemove(rowId, entry.name);
      }
      rowRegistry.delete(rowId);
      tr.remove();
    });

    dupBtn.addEventListener("click", function () {
      const entry = rowRegistry.get(rowId);
      const newRow = makeRow();
      const newEntry = rowRegistry.get(newRow.dataset.rowId);
      if (!entry || !newEntry) return;
      // Copy category + description; not name (would dup), not impls (cycle risk).
      if (entry.tomSelectInstances.category) {
        newEntry.tomSelectInstances.category.setValue(
          entry.tomSelectInstances.category.getValue()
        );
      }
      newRow.querySelector("textarea").value = tr.querySelector("textarea").value;
    });

    return tr;
  }

  // ---------------------------------------------------------------------------
  // Submit
  // ---------------------------------------------------------------------------
  function collectRow(tr) {
    const rowId = tr.dataset.rowId;
    const entry = rowRegistry.get(rowId);
    const nameInput = tr.querySelector("input[type='text']");
    const descTextarea = tr.querySelector("textarea");
    const name = normalize(nameInput.value || "");
    const category = (entry && entry.category) || "general";
    const ts = entry && entry.tomSelectInstances;
    const implication_names = ts && ts.implications ? ts.implications.getValue() : [];
    const aliases = ts && ts.aliases ? ts.aliases.getValue() : [];
    return {
      client_id: tr.dataset.clientId,
      name: name,
      category: category,
      description: (descTextarea && descTextarea.value) || null,
      aliases: Array.isArray(aliases) ? aliases : [aliases].filter(Boolean),
      implication_names: Array.isArray(implication_names)
        ? implication_names
        : [implication_names].filter(Boolean),
    };
  }

  function clearRowError(tr) {
    tr.classList.remove("row-error");
    tr.title = "";
  }

  function markRowError(tr, message) {
    tr.classList.add("row-error");
    tr.title = message;
  }

  function submit() {
    const trs = Array.from(tbody.querySelectorAll("tr"));
    if (trs.length === 0) return;

    // Client-side validation: name required, unique within batch.
    const rows = trs.map(collectRow);
    const seen = new Map();
    rows.forEach(function (r, i) {
      if (!r.name) {
        markRowError(trs[i], "Name is required");
        return;
      }
      if (seen.has(r.name)) {
        markRowError(trs[seen.get(r.name)], "Duplicate name in batch");
        markRowError(trs[i], "Duplicate name in batch");
      } else {
        clearRowError(trs[i]);
        seen.set(r.name, i);
      }
    });

    fetch(REF.submitUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tags: rows }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        const byClientId = new Map();
        data.results.forEach(function (res) { byClientId.set(res.client_id, res); });
        trs.forEach(function (tr) {
          const res = byClientId.get(tr.dataset.clientId);
          if (!res) return;
          if (res.success) {
            const entry = rowRegistry.get(tr.dataset.rowId);
            if (entry) {
              Object.values(entry.tomSelectInstances).forEach(function (ts) {
                try { ts.destroy(); } catch (e) {}
              });
              rowRegistry.delete(tr.dataset.rowId);
            }
            tr.remove();
          } else {
            markRowError(tr, res.error || "Failed");
          }
        });
        if (window.notyf) {
          window.notyf.success(
            "Created " + data.created_count + " tag(s); " + data.failed_count + " failed."
          );
        }
      })
      .catch(function (err) {
        if (window.notyf) window.notyf.error("Submit failed: " + err);
      });
  }

  // ---------------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------------
  function init() {
    if (!tbody || !addRowBtn || !submitBtn) return;
    addRowBtn.addEventListener("click", function () { makeRow(); });
    submitBtn.addEventListener("click", submit);
    makeRow();
    makeRow();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
