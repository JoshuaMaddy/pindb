// =============================================================================
// PinDB Bulk Tag Creation
//
// Spreadsheet-style row entry for tags. Each row has Name, Category,
// Implications (multi-select), Aliases (multi-select with create), and
// Description. Category changes broadcast to sibling rows' implication
// pickers so chips re-color reactively. Implication search merges DB hits
// (via /bulk/options/tag) with batch-local rows still being created.
//
// Reads window.BULK_TAG_REF (injected by templates/bulk/tag.py), including
// nameCheckUrl for HTMX duplicate-name hints.
// =============================================================================

(function () {
  "use strict";

  var _tagRefEl = document.getElementById("bulk-tag-ref-data");
  if (_tagRefEl && _tagRefEl.textContent && !window.BULK_TAG_REF) {
    try {
      window.BULK_TAG_REF = JSON.parse(_tagRefEl.textContent);
    } catch {}
  }

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
      Math.random().toString(36).slice(2, 10) + "-" + Date.now().toString(36)
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
        ts.updateOption(
          item.value,
          Object.assign({}, ts.options[item.value], item),
        );
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
    const tagSelectHelpers =
      (window.TagSelect && window.TagSelect.tagSingleSelectCallbacks) ||
      (() => ({}));
    const tagSelectOptions = tagSelectHelpers();
    const helperOnChange = tagSelectOptions.onChange;
    tagSelectOptions.onChange = function (value) {
      if (helperOnChange) helperOnChange.call(this, value);
      const entry = rowRegistry.get(rowId);
      if (!entry) return;
      entry.category = value || "general";
      if (entry.name) {
        broadcastUpsert(rowId, {
          value: entry.name,
          text: entry.name,
          category: entry.category,
        });
      }
    };
    const ts = new TS(
      selectEl,
      Object.assign(
        {
          valueField: "value",
          labelField: "text",
          searchField: ["text"],
          maxItems: 1,
          plugins: ["caret_position"],
          dropdownParent: "body",
          render: {
            option: window.TagSelect && window.TagSelect.tagOptionRender,
            item: window.TagSelect && window.TagSelect.tagItemRender,
          },
        },
        tagSelectOptions,
      ),
    );
    return ts;
  }

  // ---------------------------------------------------------------------------
  // Implication multi-select for a row. Loads DB hits + merges local rows.
  // ---------------------------------------------------------------------------
  function buildImplicationsSelect(selectEl, rowId) {
    const TS = window.TomSelect;
    const lucideHelpers =
      (window.TagSelect && window.TagSelect.tagSelectLucideCallbacks) ||
      (() => ({}));

    const ts = new TS(
      selectEl,
      Object.assign(
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
              .then(function (r) {
                return r.json();
              })
              .then(function (results) {
                // Merge local row entries (other rows) matching the query.
                const q = query.toLowerCase();
                rowRegistry.forEach(function (other, otherRowId) {
                  if (otherRowId === rowId) return;
                  if (!other.name) return;
                  if (q && other.name.indexOf(q) === -1) return;
                  if (
                    results.find(function (r) {
                      return r.value === other.name;
                    })
                  )
                    return;
                  results.push({
                    value: other.name,
                    text: other.name,
                    category: other.category || "general",
                  });
                });
                callback(results);
              })
              .catch(function () {
                callback();
              });
          },
          render: {
            option: window.TagSelect && window.TagSelect.tagOptionRender,
            item: window.TagSelect && window.TagSelect.tagItemRender,
          },
        },
        lucideHelpers(),
      ),
    );
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
      dropdownParent: "body",
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
    tr.className = "bulk-data-row border-b border-lightest";

    const nameTd = document.createElement("td");
    nameTd.className = "bulk-td";
    const nameInput = document.createElement("input");
    nameInput.type = "text";
    nameInput.required = true;
    nameInput.className =
      "w-full bg-transparent border border-lightest rounded px-1 py-0.5";
    nameInput.placeholder = "tag_name";
    if (REF.nameCheckUrl) {
      nameInput.setAttribute("name", "name");
      nameInput.setAttribute("hx-get", REF.nameCheckUrl);
      nameInput.setAttribute("hx-trigger", "input changed delay:1s, search");
      nameInput.setAttribute(
        "hx-target",
        "#bulk-tag-name-feedback-" + rowId,
      );
      nameInput.setAttribute("hx-swap", "innerHTML");
      nameInput.setAttribute(
        "hx-vals",
        JSON.stringify({ kind: "tag" }),
      );
      const nameWrap = document.createElement("div");
      nameWrap.className = "name-availability-field flex flex-col gap-1";
      nameWrap.appendChild(nameInput);
      const nameFeedback = document.createElement("div");
      nameFeedback.id = "bulk-tag-name-feedback-" + rowId;
      nameFeedback.className = "name-availability-feedback";
      nameWrap.appendChild(nameFeedback);
      nameTd.appendChild(nameWrap);
    } else {
      nameTd.appendChild(nameInput);
    }

    const categoryTd = document.createElement("td");
    categoryTd.className = "bulk-td";
    const categorySelect = document.createElement("select");
    categoryTd.appendChild(categorySelect);

    const implsTd = document.createElement("td");
    implsTd.className = "bulk-td";
    const implsSelect = document.createElement("select");
    implsSelect.multiple = true;
    implsTd.appendChild(implsSelect);

    const aliasesTd = document.createElement("td");
    aliasesTd.className = "bulk-td";
    const aliasesSelect = document.createElement("select");
    aliasesSelect.multiple = true;
    aliasesTd.appendChild(aliasesSelect);

    const descTd = document.createElement("td");
    descTd.className = "bulk-td min-w-20";
    descTd.dataset.colType = "description";
    const descInput = document.createElement("textarea");
    descInput.rows = 1;
    descInput.className =
      "w-full min-w-20 bg-transparent border border-lightest rounded px-1 py-0.5";
    descTd.appendChild(descInput);

    const actionsTd = document.createElement("td");
    actionsTd.className = "bulk-td";
    const actionsWrap = document.createElement("div");
    actionsWrap.className = "flex gap-1 justify-center";
    const dupBtn = document.createElement("button");
    dupBtn.type = "button";
    dupBtn.className = "dup-btn icon-btn";
    dupBtn.title = "Duplicate row";
    dupBtn.setAttribute("aria-label", "Duplicate row");
    dupBtn.innerHTML = '<i data-lucide="copy"></i>';
    const delBtn = document.createElement("button");
    delBtn.type = "button";
    delBtn.className = "del-btn icon-btn";
    delBtn.title = "Delete row";
    delBtn.setAttribute("aria-label", "Delete row");
    delBtn.innerHTML = '<i data-lucide="trash-2"></i>';
    actionsWrap.appendChild(dupBtn);
    actionsWrap.appendChild(delBtn);
    actionsTd.appendChild(actionsWrap);

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
          {
            value: newName,
            text: newName,
            category: entry.category || "general",
          },
          oldName,
        );
      } else if (oldName) {
        broadcastRemove(rowId, oldName);
      }
    });

    delBtn.addEventListener("click", function () {
      const entry = rowRegistry.get(rowId);
      if (entry) {
        Object.values(entry.tomSelectInstances).forEach(function (ts) {
          try {
            ts.destroy();
          } catch {}
        });
        if (entry.name) broadcastRemove(rowId, entry.name);
      }
      rowRegistry.delete(rowId);
      tr.remove();
      updateSubmitLabel();
    });

    dupBtn.addEventListener("click", function () {
      const entry = rowRegistry.get(rowId);
      const newRow = makeRow();
      const newEntry = rowRegistry.get(newRow.dataset.rowId);
      if (!entry || !newEntry) return;
      // Copy category + description; not name (would dup), not impls (cycle risk).
      if (entry.tomSelectInstances.category) {
        newEntry.tomSelectInstances.category.setValue(
          entry.tomSelectInstances.category.getValue(),
        );
      }
      newRow.querySelector("textarea").value =
        tr.querySelector("textarea").value;
      updateSubmitLabel();
    });

    if (window.lucide) lucide.createIcons({ nodes: [tr] });
    if (window.htmx) htmx.process(tr);

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
    const implication_names =
      ts && ts.implications ? ts.implications.getValue() : [];
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

  function notifySuccess(message) {
    if (window.pindbNotyf) window.pindbNotyf.success(message);
  }

  function notifyError(message) {
    if (window.pindbNotyf) {
      window.pindbNotyf.error(message);
    } else {
      alert(message);
    }
  }

  function setLucideIcon(container, iconName) {
    const existing =
      container.querySelector("i") ?? container.querySelector("svg");
    const el = document.createElement("i");
    el.setAttribute("data-lucide", iconName);
    if (existing) {
      existing.replaceWith(el);
    } else {
      container.prepend(el);
    }
    if (window.lucide) lucide.createIcons({ nodes: [container] });
  }

  function escHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function destroyRow(tr) {
    const entry = rowRegistry.get(tr.dataset.rowId);
    if (entry) {
      Object.values(entry.tomSelectInstances).forEach(function (ts) {
        try {
          ts.destroy();
        } catch {}
      });
      rowRegistry.delete(tr.dataset.rowId);
    }
    tr.remove();
  }

  function updateSubmitLabel() {
    const label = document.getElementById("bulk-tag-submit-label");
    if (!label) return;
    const count = tbody.querySelectorAll("tr.bulk-data-row").length;
    label.textContent = "Submit (" + count + ")";
  }

  async function submit() {
    const trs = Array.from(tbody.querySelectorAll("tr"));
    if (trs.length === 0) return;

    // Client-side validation: name required, unique within batch.
    const rows = trs.map(collectRow);
    const seen = new Map();
    let allValid = true;
    rows.forEach(function (r, i) {
      if (!r.name) {
        markRowError(trs[i], "Name is required");
        allValid = false;
        return;
      }
      if (seen.has(r.name)) {
        markRowError(trs[seen.get(r.name)], "Duplicate name in batch");
        markRowError(trs[i], "Duplicate name in batch");
        allValid = false;
      } else {
        clearRowError(trs[i]);
        seen.set(r.name, i);
      }
    });
    if (!allValid) {
      notifyError("Fix highlighted rows before submitting.");
      return;
    }

    submitBtn.disabled = true;
    setLucideIcon(submitBtn, "loader-circle");

    try {
      const response = await fetch(REF.submitUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tags: rows }),
      });
      if (!response.ok) {
        const detail = await response.text();
        throw new Error("Server error " + response.status + ": " + detail);
      }
      const data = await response.json();
      handleSubmitResult(data, trs);
    } catch (err) {
      console.error("Submit failed", err);
      notifyError("Submit failed: " + (err && err.message ? err.message : err));
    } finally {
      submitBtn.disabled = false;
      setLucideIcon(submitBtn, "upload");
    }
  }

  function handleSubmitResult(result, trs) {
    const byClientId = new Map();
    result.results.forEach(function (res) {
      byClientId.set(res.client_id, res);
    });
    trs.forEach(function (tr) {
      const res = byClientId.get(tr.dataset.clientId);
      if (!res) return;
      if (res.success) {
        destroyRow(tr);
      } else {
        markRowError(tr, res.error || "Failed");
      }
    });
    updateSubmitLabel();

    if (tbody.querySelectorAll("tr.bulk-data-row").length === 0) {
      makeRow();
      updateSubmitLabel();
    }

    if (result.failed_count > 0) {
      notifyError("Failed rows remain in the table — fix errors and resubmit.");
    } else {
      notifySuccess(
        "Created " +
          result.created_count +
          " tag" +
          (result.created_count === 1 ? "" : "s") +
          ".",
      );
    }
    showSuccessModal(result);
  }

  function showSuccessModal(result) {
    const modal = document.getElementById("bulk-tag-success-modal");
    const grid = document.getElementById("bulk-tag-modal-grid");
    const title = document.getElementById("bulk-tag-modal-title");
    if (!modal || !grid || !title) return;

    title.textContent =
      result.created_count +
      " tag" +
      (result.created_count === 1 ? "" : "s") +
      " created" +
      (result.failed_count ? ", " + result.failed_count + " failed" : "");

    grid.innerHTML = "";
    result.results
      .filter(function (row) {
        return row.success;
      })
      .forEach(function (row) {
        const card = document.createElement("a");
        card.href = "/get/tag/" + row.tag_id;
        card.className =
          "flex flex-col gap-1 items-center border border-lightest rounded-lg p-2 hover:border-accent no-underline text-base-text text-center";
        card.innerHTML =
          '<i data-lucide="tag" class="w-8 h-8"></i>' +
          '<span class="text-xs truncate w-full text-center">' +
          escHtml(row.tag_name || "") +
          "</span>";
        grid.appendChild(card);
      });

    if (result.failed_count > 0) {
      const errTitle = document.createElement("p");
      errTitle.className = "col-span-full text-sm text-error-main font-semibold";
      errTitle.textContent =
        "Failed rows remain in the table — fix errors and resubmit.";
      grid.appendChild(errTitle);
    }

    modal.classList.remove("hidden");
    if (window.lucide) lucide.createIcons({ nodes: [modal] });
  }

  function closeSuccessModal() {
    const modal = document.getElementById("bulk-tag-success-modal");
    if (modal) modal.classList.add("hidden");
  }

  // ---------------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------------
  function init() {
    if (!tbody || !addRowBtn || !submitBtn) return;
    addRowBtn.addEventListener("click", function () {
      makeRow();
      updateSubmitLabel();
    });
    submitBtn.addEventListener("click", submit);
    const closeBtn = document.getElementById("bulk-tag-modal-close-btn");
    if (closeBtn) closeBtn.addEventListener("click", closeSuccessModal);
    makeRow();
    makeRow();
    updateSubmitLabel();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
