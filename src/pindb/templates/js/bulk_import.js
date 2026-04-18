// =============================================================================
// PinDB Bulk Import
// =============================================================================

(function () {
  "use strict";

  // ---------------------------------------------------------------------------
  // Module state
  // ---------------------------------------------------------------------------

  const REF = window.BULK_REF;


  const BULK_STORAGE_KEY = "bulk_persist";
  const bulkNavType =
    (performance.getEntriesByType("navigation")[0] || {}).type || "navigate";

  /** @type {Map<string, {frontImageGuid: string|null, backImageGuid: string|null}>} */
  const rowState = new Map();

  /**
   * Per-row Tom Select instances.
   * @type {Map<string, {shops, tags, artists, pinSets, acquisition, currency, funding}>}
   */
  const rowTS = new Map();

  /** Which grades sub-row is currently open (rowId or null). */
  let openGradesRowId = null;

  /** Which links popover is currently open (rowId or null). */
  let openLinksRowId = null;

  /** Copy/paste clipboard: {type: string, values: any} */
  let cellClipboard = null;

  /** Currently hovered image drop cell: {rowId, side} | null */
  let _hoveredImageDropCell = null;

  let rowCounter = 0;

  /**
   * Locally-created Tom Select options, keyed by entityType.
   * When a user creates a new option (e.g. tag "red") it lives here so other
   * rows of the same field type can find it before the DB is updated.
   * @type {Map<string, Map<string, {value: string, text: string}>>}
   */
  const localOptionsByType = new Map();

  // ---------------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------------

  window.addEventListener("load", function () {
    initColumnVisibility();
    wireSelectAll();
    wireHeaderButtons();
    wireHeaderPasteButtons();

    const savedBulk = sessionStorage.getItem(BULK_STORAGE_KEY);
    if (bulkNavType === "reload" && savedBulk) {
      try {
        JSON.parse(savedBulk).forEach((pin) => addRow(pin));
      } catch (_) {
        addRow();
      }
    } else {
      sessionStorage.removeItem(BULK_STORAGE_KEY);
      addRow();
    }

    document.addEventListener("paste", (e) => {
      if (!_hoveredImageDropCell) return;
      const items = e.clipboardData?.items;
      if (!items) return;
      for (const item of items) {
        if (item.type.startsWith("image/")) {
          const file = item.getAsFile();
          if (!file) continue;
          uploadImage(_hoveredImageDropCell.rowId, _hoveredImageDropCell.side, file);
          e.preventDefault();
          break;
        }
      }
    });

    document.addEventListener("input", function (e) {
      debouncedSaveBulkState();
      if (e.target.matches('input[data-field="name"]')) syncNameColWidth();
    });
    document.addEventListener("change", debouncedSaveBulkState);
  });

  // ---------------------------------------------------------------------------
  // Bulk state persistence (sessionStorage)
  // ---------------------------------------------------------------------------

  let saveBulkDebounceTimer = null;

  function debouncedSaveBulkState() {
    clearTimeout(saveBulkDebounceTimer);
    saveBulkDebounceTimer = setTimeout(saveBulkState, 300);
  }

  function saveBulkState() {
    const rows = document.querySelectorAll("#bulk-tbody > tr.bulk-data-row");
    const pins = [];
    rows.forEach((tr) => {
      try {
        pins.push(collectRowData(tr.dataset.rowId));
      } catch (_) {}
    });
    sessionStorage.setItem(BULK_STORAGE_KEY, JSON.stringify(pins));
  }

  // ---------------------------------------------------------------------------
  // Column visibility (localStorage)
  // ---------------------------------------------------------------------------

  const COL_STORAGE_KEY = "bulk_visible_cols";

  function initColumnVisibility() {
    const saved = JSON.parse(localStorage.getItem(COL_STORAGE_KEY) || "{}");

    document.querySelectorAll(".col-toggle-check").forEach((checkbox) => {
      const col = checkbox.dataset.col;
      if (col in saved) checkbox.checked = saved[col];
      applyColumnVisibility(col, checkbox.checked);
      checkbox.addEventListener("change", () => {
        applyColumnVisibility(col, checkbox.checked);
        const state = JSON.parse(localStorage.getItem(COL_STORAGE_KEY) || "{}");
        state[col] = checkbox.checked;
        localStorage.setItem(COL_STORAGE_KEY, JSON.stringify(state));
      });
    });
  }

  function applyColumnVisibility(col, visible) {
    document.querySelectorAll(`[data-col="${col}"]`).forEach((el) => {
      el.style.display = visible ? "" : "none";
    });
  }

  // ---------------------------------------------------------------------------
  // Header buttons
  // ---------------------------------------------------------------------------

  function wireHeaderButtons() {
    document
      .getElementById("add-row-btn")
      .addEventListener("click", () => addRow());
    document.getElementById("submit-btn").addEventListener("click", submitAll);
    document
      .getElementById("modal-close-btn")
      .addEventListener("click", closeModal);
    document
      .getElementById("select-all-rows")
      .addEventListener("change", (e) => {
        document.querySelectorAll(".row-checkbox").forEach((cb) => {
          cb.checked = e.target.checked;
        });
      });
  }

  function updateSubmitLabel() {
    const count = document.querySelectorAll(
      "#bulk-tbody > tr.bulk-data-row",
    ).length;
    document.getElementById("submit-label").textContent = `Submit (${count})`;
  }

  // ---------------------------------------------------------------------------
  // Row management
  // ---------------------------------------------------------------------------

  function addRow(prefill) {
    const id = `row-${++rowCounter}`;
    rowState.set(id, { frontImageGuid: null, backImageGuid: null });

    const tbody = document.getElementById("bulk-tbody");

    const tr = document.createElement("tr");
    tr.id = id;
    tr.className = "bulk-data-row border-b border-pin-border";
    tr.dataset.rowId = id;
    tr.innerHTML = buildRowHTML(id);
    tbody.appendChild(tr);

    initRow(id, prefill);
    updateSubmitLabel();
    saveBulkState();
    return id;
  }

  function deleteRow(rowId) {
    if (openGradesRowId === rowId) closeGrades(rowId);
    if (openLinksRowId === rowId) closeLinks(rowId);

    const ts = rowTS.get(rowId);
    if (ts) {
      Object.values(ts).forEach(
        (instance) => instance && instance.destroy && instance.destroy(),
      );
      rowTS.delete(rowId);
    }
    rowState.delete(rowId);

    const tr = document.getElementById(rowId);
    if (tr) tr.remove();
    updateSubmitLabel();
    saveBulkState();
  }

  function duplicateRow(rowId) {
    const prefill = collectRowData(rowId);
    // Don't duplicate images — they're unique per pin
    prefill.front_image_guid = null;
    prefill.back_image_guid = null;
    const newId = addRow(prefill);
    // Scroll new row into view
    document.getElementById(newId)?.scrollIntoView({ block: "nearest" });
  }

  // ---------------------------------------------------------------------------
  // Row HTML template
  // ---------------------------------------------------------------------------

  function buildRowHTML(id) {
    return `
      <td class="bulk-td bulk-sticky-td bulk-sticky-col-0 w-8 text-center">
        <input type="checkbox" class="row-checkbox">
      </td>

      <!-- Front image -->
      <td class="bulk-td bulk-sticky-td bulk-sticky-col-1"
          data-col-type="front_image"
          style="width:88px;min-width:88px;">
        <div class="image-drop-cell" data-row="${id}" data-side="front"
             style="width:72px;height:72px;border:2px dashed var(--color-pin-border);border-radius:8px;display:flex;align-items:center;justify-content:center;cursor:pointer;background-size:cover;background-position:center;font-size:10px;text-align:center;padding:4px;">
          Front
        </div>
        <input type="file" class="img-file-input hidden" data-row="${id}" data-side="front"
               accept="image/png,image/jpeg,image/jpg,image/webp">
        <div class="img-spinner hidden absolute inset-0 flex items-center justify-center bg-black/30 rounded" data-row="${id}" data-side="front">
          <i data-lucide="loader-circle" class="animate-spin"></i>
        </div>
      </td>

      <!-- Back image -->
      <td class="bulk-td relative" data-col-type="back_image">
        <div class="image-drop-cell" data-row="${id}" data-side="back"
             style="width:72px;height:72px;border:2px dashed var(--color-pin-border);border-radius:8px;display:flex;align-items:center;justify-content:center;cursor:pointer;background-size:cover;background-position:center;font-size:10px;text-align:center;padding:4px;">
          Back
        </div>
        <input type="file" class="img-file-input hidden" data-row="${id}" data-side="back"
               accept="image/png,image/jpeg,image/jpg,image/webp">
        <div class="img-spinner hidden absolute inset-0 flex items-center justify-center bg-black/30 rounded" data-row="${id}" data-side="back">
          <i data-lucide="loader-circle" class="animate-spin"></i>
        </div>
      </td>

      <!-- Name -->
      <td class="bulk-td bulk-sticky-td bulk-sticky-col-2 copyable-cell"
          data-col-type="name">
        <input type="text" class="bulk-input w-full" data-row="${id}" data-field="name" placeholder="Pin name" autocomplete="off">
      </td>

      <!-- Shops -->
      <td class="bulk-td copyable-cell" data-col-type="shops">
        <select class="bulk-ts-multi" data-row="${id}" data-field="shops" multiple></select>
      </td>

      <!-- Acquisition -->
      <td class="bulk-td copyable-cell" data-col-type="acquisition_type">
        <select class="bulk-ts-single" data-row="${id}" data-field="acquisition_type"></select>
      </td>

      <!-- Grades -->
      <td class="bulk-td text-center copyable-cell" data-col-type="grades">
        <button type="button" class="grades-toggle-btn w-full" data-row="${id}">
          Grades (<span class="grades-count" data-row="${id}">0</span>)
        </button>
      </td>

      <!-- Currency -->
      <td class="bulk-td copyable-cell" data-col-type="currency_id">
        <select class="bulk-ts-single" data-row="${id}" data-field="currency_id"></select>
      </td>

      <!-- Tags -->
      <td class="bulk-td copyable-cell" data-col-type="tags">
        <select class="bulk-ts-multi" data-row="${id}" data-field="tags" multiple></select>
      </td>

      <!-- Artists (optional) -->
      <td class="bulk-td copyable-cell" data-col="artists" data-col-type="artists">
        <select class="bulk-ts-multi" data-row="${id}" data-field="artists" multiple></select>
      </td>

      <!-- Pin Sets (optional) -->
      <td class="bulk-td copyable-cell" data-col="pin_sets" data-col-type="pin_sets">
        <select class="bulk-ts-multi" data-row="${id}" data-field="pinSets" multiple></select>
      </td>

      <!-- Limited Edition (optional) -->
      <td class="bulk-td" data-col="limited_edition" data-col-type="limited_edition">
        <select class="bulk-ts-single" data-row="${id}" data-field="limited_edition"></select>
      </td>

      <!-- Number Produced (optional) -->
      <td class="bulk-td copyable-cell" data-col="number_produced" data-col-type="number_produced">
        <input type="number" class="bulk-input w-full" data-row="${id}" data-field="number_produced" min="0" step="1" placeholder="—">
      </td>

      <!-- Release Date (optional) -->
      <td class="bulk-td copyable-cell" data-col="release_date" data-col-type="release_date">
        <input type="date" class="bulk-input w-full" data-row="${id}" data-field="release_date">
      </td>

      <!-- End Date (optional) -->
      <td class="bulk-td copyable-cell" data-col="end_date" data-col-type="end_date">
        <input type="date" class="bulk-input w-full" data-row="${id}" data-field="end_date">
      </td>

      <!-- Funding Type (optional) -->
      <td class="bulk-td copyable-cell" data-col="funding_type" data-col-type="funding_type">
        <select class="bulk-ts-single" data-row="${id}" data-field="funding_type"></select>
      </td>

      <!-- Posts (optional) -->
      <td class="bulk-td copyable-cell" data-col="posts" data-col-type="posts">
        <input type="number" class="bulk-input w-full" data-row="${id}" data-field="posts" min="1" step="1" value="1" placeholder="1">
      </td>

      <!-- Width (optional) -->
      <td class="bulk-td copyable-cell" data-col="width" data-col-type="width">
        <input type="text" class="bulk-input w-full" data-row="${id}" data-field="width" pattern="${window.BULK_REF.magnitudeInputPattern || ''}" autocomplete="off" placeholder="e.g. 40mm or 1.5in">
      </td>

      <!-- Height (optional) -->
      <td class="bulk-td copyable-cell" data-col="height" data-col-type="height">
        <input type="text" class="bulk-input w-full" data-row="${id}" data-field="height" pattern="${window.BULK_REF.magnitudeInputPattern || ''}" autocomplete="off" placeholder="e.g. 40mm or 1.5in">
      </td>

      <!-- Links (optional) -->
      <td class="bulk-td" data-col="links" data-col-type="links">
        <button type="button" class="links-toggle-btn w-full" data-row="${id}">
          Links (<span class="links-count" data-row="${id}">0</span>)
        </button>
      </td>

      <!-- Description (optional) -->
      <td class="bulk-td copyable-cell" data-col="description" data-col-type="description">
        <input type="text" class="bulk-input w-full" data-row="${id}" data-field="description" placeholder="—">
      </td>

      <!-- Actions -->
      <td class="bulk-td">
        <div class="flex gap-1 justify-center">
          <button type="button" class="dup-btn icon-btn" data-row="${id}" title="Duplicate row">
            <i data-lucide="copy"></i>
          </button>
          <button type="button" class="del-btn icon-btn" data-row="${id}" title="Delete row">
            <i data-lucide="trash-2"></i>
          </button>
        </div>
      </td>
    `;
  }

  // ---------------------------------------------------------------------------
  // Row initialisation (Tom Select, images, events, copy/paste, prefill)
  // ---------------------------------------------------------------------------

  function initRow(rowId, prefill) {
    const tr = document.getElementById(rowId);

    // Tom Selects
    const tsMap = {};

    // Multi-selects — live DB search + local option registry
    const multiConfigs = [
      { field: "shops", entityType: "shop" },
      { field: "tags", entityType: "tag" },
      { field: "artists", entityType: "artist" },
      { field: "pinSets", entityType: "pin_set" },
    ];
    const noResultsRender = {
      no_results: (data) => {
        const msg = data.input && data.input.length > 0 ? "No results found" : "Start typing to search…";
        return `<div class="no-results">${msg}</div>`;
      },
    };

    multiConfigs.forEach(({ field, entityType }) => {
      const sel = tr.querySelector(`select[data-field="${field}"]`);
      if (!sel) return;
      const tsOpts = {
        load: (query, callback) => {
          fetch(
            `${REF.optionsBaseUrl}/${entityType}?q=${encodeURIComponent(query)}`,
          )
            .then((res) => res.json())
            .then((results) => {
              // Merge in locally-created options that match the query
              const locals = localOptionsByType.get(entityType);
              if (locals) {
                const q = query.toLowerCase();
                locals.forEach((item) => {
                  if (
                    (!q || item.text.toLowerCase().includes(q)) &&
                    !results.find((r) => String(r.value) === String(item.value))
                  ) {
                    results.push(item);
                  }
                });
              }
              callback(results);
            })
            .catch(() => callback());
        },
        shouldLoad: (q) => q.length > 0,
        create: (input, callback) => {
          const item = { value: input, text: input };
          // Register in local registry
          if (!localOptionsByType.has(entityType)) {
            localOptionsByType.set(entityType, new Map());
          }
          localOptionsByType.get(entityType).set(input, item);
          // Broadcast to all other existing instances of same type
          broadcastLocalOption(entityType, input, item, rowId, field);
          callback(item);
        },
        plugins: ["remove_button", "caret_position"],
        maxItems: null,
        persist: false,
        dropdownParent: "body",
        render: { ...noResultsRender },
      };
      if (entityType === "tag") {
        tsOpts.render = {
          ...noResultsRender,
          item: TagSelect.tagItemRender,
          option: TagSelect.tagOptionRender,
        };
        Object.assign(tsOpts, TagSelect.tagSelectLucideCallbacks());
      }
      const instance = new TomSelect(sel, tsOpts);
      // Inject any options already created in other rows
      const existingLocals = localOptionsByType.get(entityType);
      if (existingLocals) {
        existingLocals.forEach((item) => {
          if (!instance.options[item.value]) instance.addOption(item);
        });
      }
      tsMap[field] = instance;
    });

    // Acquisition type single-select (required)
    const acqSel = tr.querySelector(`select[data-field="acquisition_type"]`);
    tsMap["acquisition_type"] = new TomSelect(acqSel, {
      options: REF.acquisitionTypes,
      create: false,
      dropdownParent: "body",
    });

    // Currency single-select
    const currSel = tr.querySelector(`select[data-field="currency_id"]`);
    tsMap["currency_id"] = new TomSelect(currSel, {
      options: REF.currencies,
      create: false,
      dropdownParent: "body",
    });
    tsMap["currency_id"].setValue(String(REF.defaultCurrencyId));

    // Limited edition single-select
    const leSel = tr.querySelector(`select[data-field="limited_edition"]`);
    tsMap["limited_edition"] = new TomSelect(leSel, {
      options: [
        { value: "", text: "—" },
        { value: "true", text: "Yes" },
        { value: "false", text: "No" },
      ],
      create: false,
      dropdownParent: "body",
    });

    // Funding type single-select
    const fundSel = tr.querySelector(`select[data-field="funding_type"]`);
    tsMap["funding_type"] = new TomSelect(fundSel, {
      options: [{ value: "", text: "—" }, ...REF.fundingTypes],
      create: false,
      dropdownParent: "body",
    });

    rowTS.set(rowId, tsMap);

    // Image drops
    tr.querySelectorAll(".image-drop-cell").forEach((box) => {
      const side = box.dataset.side;
      const fileInput = tr.querySelector(
        `input[type="file"][data-side="${side}"]`,
      );
      box.addEventListener("click", () => fileInput.click());
      box.addEventListener("mouseenter", () => { _hoveredImageDropCell = { rowId, side }; });
      box.addEventListener("mouseleave", () => { _hoveredImageDropCell = null; });
      box.addEventListener("dragover", (e) => {
        e.preventDefault();
        box.style.borderColor = "var(--color-accent)";
      });
      box.addEventListener("dragleave", () => {
        box.style.borderColor = "var(--color-pin-border)";
      });
      box.addEventListener("drop", (e) => {
        e.preventDefault();
        box.style.borderColor = "var(--color-accent)";
        const file = e.dataTransfer.files[0];
        if (file) uploadImage(rowId, side, file);
      });
      fileInput.addEventListener("change", () => {
        if (fileInput.files[0]) uploadImage(rowId, side, fileInput.files[0]);
      });
    });

    // Grades toggle
    tr.querySelector(".grades-toggle-btn").addEventListener("click", () =>
      toggleGrades(rowId),
    );

    // Links toggle
    tr.querySelector(".links-toggle-btn").addEventListener("click", () =>
      toggleLinks(rowId),
    );

    // Action buttons
    tr.querySelector(".dup-btn").addEventListener("click", () =>
      duplicateRow(rowId),
    );
    tr.querySelector(".del-btn").addEventListener("click", () =>
      deleteRow(rowId),
    );

    // Copy/paste wiring for copyable cells
    tr.querySelectorAll(".copyable-cell").forEach((td) =>
      wireCopyPaste(td, rowId),
    );

    // Re-run Lucide on new row
    if (window.lucide) lucide.createIcons({ nodes: [tr] });

    // Prefill values if duplicating
    if (prefill) applyPrefill(rowId, prefill);

    // Default grade for new rows (no prefill or prefill had no grades)
    if (!tr.dataset.grades) {
      tr.dataset.grades = JSON.stringify([{ name: "Normal", price: "" }]);
      tr.querySelector(`.grades-count[data-row="${rowId}"]`).textContent = 1;
    }

    // Apply has-clipboard to new row's cells if clipboard is active
    if (cellClipboard) {
      tr.querySelectorAll(`.copyable-cell[data-col-type="${cellClipboard.type}"]`).forEach(
        (td) => td.classList.add("has-clipboard"),
      );
    }

    // Re-apply column visibility to new cells
    document.querySelectorAll(".col-toggle-check").forEach((cb) => {
      applyColumnVisibility(cb.dataset.col, cb.checked);
    });

    // Sync name column width in case prefill name is longer
    syncNameColWidth();
  }

  function applyPrefill(rowId, prefill) {
    const tr = document.getElementById(rowId);
    const ts = rowTS.get(rowId);

    if (prefill.name)
      tr.querySelector(`input[data-field="name"]`).value = prefill.name;
    if (prefill.number_produced != null)
      tr.querySelector(`input[data-field="number_produced"]`).value =
        prefill.number_produced;
    if (prefill.posts)
      tr.querySelector(`input[data-field="posts"]`).value = prefill.posts;
    if (prefill.width)
      tr.querySelector(`input[data-field="width"]`).value = prefill.width;
    if (prefill.height)
      tr.querySelector(`input[data-field="height"]`).value = prefill.height;
    if (prefill.description)
      tr.querySelector(`input[data-field="description"]`).value =
        prefill.description;
    if (prefill.release_date)
      tr.querySelector(`input[data-field="release_date"]`).value =
        prefill.release_date;
    if (prefill.end_date)
      tr.querySelector(`input[data-field="end_date"]`).value = prefill.end_date;

    const prefillMulti = (instance, opts) => {
      if (!opts?.length || !instance) return;
      opts.forEach((opt) => {
        const item = typeof opt === "object" ? opt : { value: opt, text: opt };
        if (!instance.options[item.value]) instance.addOption(item);
      });
      instance.addItems(opts.map((opt) => (typeof opt === "object" ? opt.value : opt)));
    };
    prefillMulti(ts.shops, prefill.shop_options ?? prefill.shop_names);
    prefillMulti(ts.tags, prefill.tag_options ?? prefill.tag_names);
    prefillMulti(ts.artists, prefill.artist_options ?? prefill.artist_names);
    prefillMulti(ts.pinSets, prefill.pin_set_options ?? prefill.pin_set_names);
    if (prefill.acquisition_type)
      ts["acquisition_type"].setValue(prefill.acquisition_type);
    if (prefill.currency_id)
      ts["currency_id"].setValue(String(prefill.currency_id));
    if (prefill.funding_type) ts["funding_type"].setValue(prefill.funding_type);
    if (prefill.limited_edition != null)
      ts["limited_edition"].setValue(String(prefill.limited_edition));

    if (prefill.grades?.length) {
      tr.dataset.grades = JSON.stringify(prefill.grades);
      const validCount = prefill.grades.filter((g) => g.name).length;
      tr.querySelector(`.grades-count[data-row="${rowId}"]`).textContent =
        validCount;
    }

    if (prefill.links?.length) {
      tr.dataset.links = JSON.stringify(prefill.links);
      const validCount = prefill.links.filter((l) => l.trim()).length;
      tr.querySelector(`.links-count[data-row="${rowId}"]`).textContent =
        validCount;
    }
  }

  // ---------------------------------------------------------------------------
  // Image upload
  // ---------------------------------------------------------------------------

  async function uploadImage(rowId, side, file) {
    const tr = document.getElementById(rowId);
    const box = tr.querySelector(`.image-drop-cell[data-side="${side}"]`);
    const spinner = tr.querySelector(`.img-spinner[data-side="${side}"]`);

    spinner.classList.remove("hidden");

    try {
      const fd = new FormData();
      fd.append("image", file);
      const res = await fetch(REF.uploadImageUrl, { method: "POST", body: fd });
      const { guid } = await res.json();

      const key = side === "front" ? "frontImageGuid" : "backImageGuid";
      rowState.get(rowId)[key] = guid;

      // Show preview
      const reader = new FileReader();
      reader.onload = (e) => {
        box.style.backgroundImage = `url('${e.target.result}')`;
        box.textContent = "";
        box.style.borderColor = "var(--color-accent)";
      };
      reader.readAsDataURL(file);
    } catch (err) {
      console.error("Image upload failed", err);
      box.textContent = "Upload failed";
    } finally {
      spinner.classList.add("hidden");
    }
  }

  // ---------------------------------------------------------------------------
  // Grades sub-row
  // ---------------------------------------------------------------------------

  function toggleGrades(rowId) {
    if (openGradesRowId === rowId) {
      closeGrades(rowId);
      return;
    }
    if (openGradesRowId) closeGrades(openGradesRowId);
    openGrades(rowId);
  }

  function openGrades(rowId) {
    openGradesRowId = rowId;
    const tr = document.getElementById(rowId);
    const colCount = tr.cells.length;
    const visibleWidth = tr.closest(".overflow-x-auto")?.clientWidth ?? 900;

    // Collect existing grades from any previous sub-row data attribute
    const existing = JSON.parse(
      tr.dataset.grades || '[{"name":"Normal","price":""}]',
    );

    const subTr = document.createElement("tr");
    subTr.id = `${rowId}-grades`;
    subTr.className = "grades-sub-row bg-pin-main/50";

    const gradesJson = JSON.stringify(existing).replace(/'/g, "\\'");

    subTr.innerHTML = `
      <td colspan="${colCount}" style="padding: 0;">
        <div class="px-4 py-2" style="position: sticky; left: 0; width: ${visibleWidth}px; box-sizing: border-box;">
        <div class="flex items-center gap-2 mb-2">
          <i data-lucide="layers" class="w-4 h-4"></i>
          <span class="font-semibold text-sm">Grades for this pin</span>
        </div>
        <div x-data='{ grades: ${gradesJson.replace(/"/g, "&quot;")} }'>
          <template x-for="(grade, index) in grades" :key="index">
            <div class="grid grid-cols-[2fr_1fr_min-content] gap-2 mb-2">
              <input class="bulk-input" type="text" x-model="grades[index].name"
                     placeholder="Grade name" autocomplete="off">
              <input class="bulk-input" type="number" x-model="grades[index].price"
                     placeholder="Unknown" step="0.01" min="0">
              <button type="button"
                      @click="grades.splice(index, 1)"
                      x-show="grades.length > 1"
                      class="icon-btn text-red-200">
                <i data-lucide="minus-circle"></i>
              </button>
            </div>
          </template>
          <button type="button"
                  @click="grades.push({name:'', price:''})"
                  class="w-full mt-1">
            + Add Grade
          </button>
        </div>
        </div>
      </td>
    `;

    tr.after(subTr);
    // Init Alpine on new element
    if (window.Alpine) Alpine.initTree(subTr);
    if (window.lucide) lucide.createIcons({ nodes: [subTr] });

    tr.querySelector(".grades-toggle-btn").classList.add(
      "border-accent",
      "text-accent",
    );
  }

  function closeGrades(rowId) {
    const tr = document.getElementById(rowId);
    const subTr = document.getElementById(`${rowId}-grades`);
    if (subTr) {
      // Persist grades data back onto the parent row
      const gradesDiv = subTr.querySelector("[x-data]");
      if (gradesDiv) {
        try {
          const grades = Alpine.$data(gradesDiv).grades;
          tr.dataset.grades = JSON.stringify(grades);
          // Update count badge
          const validGrades = grades.filter((g) => g.name);
          tr.querySelector(`.grades-count[data-row="${rowId}"]`).textContent =
            validGrades.length;
        } catch (_) {}
      }
      subTr.remove();
    }
    openGradesRowId = null;
    tr.querySelector(".grades-toggle-btn").classList.remove(
      "border-accent",
      "text-accent",
    );
  }

  // ---------------------------------------------------------------------------
  // Links popover sub-row
  // ---------------------------------------------------------------------------

  function toggleLinks(rowId) {
    if (openLinksRowId === rowId) {
      closeLinks(rowId);
      return;
    }
    if (openLinksRowId) closeLinks(openLinksRowId);
    openLinks(rowId);
  }

  function openLinks(rowId) {
    openLinksRowId = rowId;
    const tr = document.getElementById(rowId);
    const colCount = tr.cells.length;
    const visibleWidth = tr.closest(".overflow-x-auto")?.clientWidth ?? 900;
    const existing = JSON.parse(tr.dataset.links || '[""]');

    const subTr = document.createElement("tr");
    subTr.id = `${rowId}-links`;
    subTr.className = "links-sub-row bg-pin-main/50";

    subTr.innerHTML = `
      <td colspan="${colCount}" style="padding: 0;">
        <div class="px-4 py-2" style="position: sticky; left: 0; width: ${visibleWidth}px; box-sizing: border-box;">
        <div class="flex items-center gap-2 mb-2">
          <i data-lucide="link" class="w-4 h-4"></i>
          <span class="font-semibold text-sm">Links for this pin</span>
        </div>
        <div x-data='{ links: ${JSON.stringify(existing).replace(/"/g, "&quot;")} }'>
          <template x-for="(link, index) in links" :key="index">
            <div class="grid grid-cols-[1fr_min-content] gap-2 mb-2">
              <input class="bulk-input" type="text" x-model="links[index]"
                     placeholder="https://..." autocomplete="off">
              <button type="button"
                      @click="links.splice(index, 1)"
                      x-show="links.length > 1"
                      class="icon-btn text-red-200">
                <i data-lucide="minus-circle"></i>
              </button>
            </div>
          </template>
          <button type="button"
                  @click="links.push('')"
                  class="w-full mt-1">
            + Add Another Link
          </button>
        </div>
        </div>
      </td>
    `;

    tr.after(subTr);
    if (window.Alpine) Alpine.initTree(subTr);
    if (window.lucide) lucide.createIcons({ nodes: [subTr] });

    tr.querySelector(".links-toggle-btn").classList.add(
      "border-accent",
      "text-accent",
    );
  }

  function closeLinks(rowId) {
    const tr = document.getElementById(rowId);
    const subTr = document.getElementById(`${rowId}-links`);
    if (subTr) {
      const linksDiv = subTr.querySelector("[x-data]");
      if (linksDiv) {
        try {
          const links = Alpine.$data(linksDiv).links;
          tr.dataset.links = JSON.stringify(links);
          const validLinks = links.filter((l) => l.trim());
          tr.querySelector(`.links-count[data-row="${rowId}"]`).textContent =
            validLinks.length;
        } catch (_) {}
      }
      subTr.remove();
    }
    openLinksRowId = null;
    tr.querySelector(".links-toggle-btn").classList.remove(
      "border-accent",
      "text-accent",
    );
  }

  // ---------------------------------------------------------------------------
  // Copy / Paste
  // ---------------------------------------------------------------------------

  function wireCopyPaste(tdEl, rowId) {
    // Don't override position:sticky (set via CSS class) with position:relative
    if (getComputedStyle(tdEl).position !== "sticky") {
      tdEl.style.position = "relative";
    }

    const copyBtn = document.createElement("button");
    copyBtn.type = "button";
    copyBtn.className = "cell-copy-btn";
    copyBtn.innerHTML = '<i data-lucide="clipboard-copy"></i>';
    copyBtn.title = "Copy cell value";
    tdEl.appendChild(copyBtn);

    const pasteBtn = document.createElement("button");
    pasteBtn.type = "button";
    pasteBtn.className = "cell-paste-btn";
    pasteBtn.innerHTML = '<i data-lucide="clipboard-paste"></i>';
    pasteBtn.title = "Paste cell value";
    tdEl.appendChild(pasteBtn);

    if (window.lucide) lucide.createIcons({ nodes: [tdEl] });

    copyBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const colType = tdEl.dataset.colType;
      const values = readCellValues(tdEl, rowId, colType);
      cellClipboard = { type: colType, values };
      copyBtn.classList.add("copied");
      setTimeout(() => copyBtn.classList.remove("copied"), 800);
      // Show paste on all same-type cells; hide on others
      refreshPasteButtons(colType);
    });

    pasteBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      if (!cellClipboard) return;
      writeCellValues(tdEl, rowId, cellClipboard.type, cellClipboard.values);
    });

    // No mouseenter/mouseleave — paste visibility is controlled by has-clipboard class
  }

  function wireHeaderPasteButtons() {
    document.querySelectorAll("th[data-col-type]").forEach((th) => {
      const pasteBtn = document.createElement("button");
      pasteBtn.type = "button";
      pasteBtn.className = "header-paste-btn hidden";
      pasteBtn.innerHTML = '<i data-lucide="clipboard-paste"></i>';
      pasteBtn.title = "Paste to all rows";
      th.appendChild(pasteBtn);

      pasteBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        if (!cellClipboard || cellClipboard.type !== th.dataset.colType) return;
        document
          .querySelectorAll("#bulk-tbody > tr.bulk-data-row")
          .forEach((tr) => {
            const rowId = tr.dataset.rowId;
            const tdEl = tr.querySelector(
              `td[data-col-type="${cellClipboard.type}"]`,
            );
            if (tdEl)
              writeCellValues(
                tdEl,
                rowId,
                cellClipboard.type,
                cellClipboard.values,
              );
          });
      });
    });
    if (window.lucide)
      lucide.createIcons({
        nodes: Array.from(document.querySelectorAll("th[data-col-type]")),
      });
  }

  function refreshPasteButtons(colType) {
    // Show paste button on cells matching copied type; hide on all others
    document.querySelectorAll(".copyable-cell").forEach((td) => {
      if (td.dataset.colType === colType) {
        td.classList.add("has-clipboard");
      } else {
        td.classList.remove("has-clipboard");
      }
    });
    // Show header paste button for matching column only
    document
      .querySelectorAll("th[data-col-type] .header-paste-btn")
      .forEach((btn) => {
        btn.classList.toggle(
          "hidden",
          btn.closest("th").dataset.colType !== colType,
        );
      });
  }

  function readCellValues(tdEl, rowId, colType) {
    const ts = rowTS.get(rowId);
    const multiFields = ["shops", "tags", "artists", "pin_sets"];
    const singleFields = ["acquisition_type", "currency_id", "funding_type"];

    if (colType === "grades") {
      const tr = document.getElementById(rowId);
      if (openGradesRowId === rowId) {
        const gradesDiv = document.querySelector(`#${rowId}-grades [x-data]`);
        try {
          return Alpine.$data(gradesDiv).grades;
        } catch (_) {}
      }
      return JSON.parse(tr.dataset.grades || "[]");
    }
    if (multiFields.includes(colType) && ts) {
      const fieldMap = { pin_sets: "pinSets" };
      const tsKey = fieldMap[colType] || colType;
      const instance = ts[tsKey];
      if (!instance) return [];
      // Return {value, text, category?} pairs so paste can addOption with full metadata
      return instance.getValue().map((v) => {
        const opt = instance.options[v] || {};
        const item = { value: v, text: opt.text || v };
        if (opt.category) item.category = opt.category;
        return item;
      });
    }
    if (singleFields.includes(colType) && ts) {
      return ts[colType]?.getValue() ?? "";
    }
    // Text / number inputs
    const input = tdEl.querySelector("input");
    return input ? input.value : "";
  }

  function writeCellValues(tdEl, rowId, colType, values) {
    const ts = rowTS.get(rowId);
    const multiFields = ["shops", "tags", "artists", "pin_sets"];
    const singleFields = ["acquisition_type", "currency_id", "funding_type"];

    if (colType === "grades") {
      const tr = document.getElementById(rowId);
      const gradesCopy = JSON.parse(JSON.stringify(values));
      tr.dataset.grades = JSON.stringify(gradesCopy);
      const validGrades = gradesCopy.filter((g) => g.name);
      tr.querySelector(`.grades-count[data-row="${rowId}"]`).textContent =
        validGrades.length;
      if (openGradesRowId === rowId) {
        closeGrades(rowId);
        openGrades(rowId);
      }
      return;
    }
    if (multiFields.includes(colType) && ts) {
      const fieldMap = { pin_sets: "pinSets" };
      const tsKey = fieldMap[colType] || colType;
      const instance = ts[tsKey];
      if (instance) {
        instance.clear(true);
        if (Array.isArray(values)) {
          values.forEach((item) => {
            const val = typeof item === "object" ? item.value : item;
            const text = typeof item === "object" ? item.text : item;
            if (!instance.options[val]) {
              const newOpt = { value: val, text };
              if (typeof item === "object" && item.category) newOpt.category = item.category;
              instance.addOption(newOpt);
            }
            instance.addItem(val, true);
          });
        }
      }
      return;
    }
    if (singleFields.includes(colType) && ts) {
      ts[colType]?.setValue(values);
      return;
    }
    const input = tdEl.querySelector("input");
    if (input) input.value = values;
  }

  // ---------------------------------------------------------------------------
  // Select-all checkbox
  // ---------------------------------------------------------------------------

  function wireSelectAll() {
    // Delegate — handled in wireHeaderButtons
  }

  // ---------------------------------------------------------------------------
  // Collect row data for submit
  // ---------------------------------------------------------------------------

  function collectRowData(rowId) {
    const tr = document.getElementById(rowId);
    const ts = rowTS.get(rowId);
    const state = rowState.get(rowId);

    const field = (name) =>
      tr.querySelector(`input[data-field="${name}"]`)?.value ?? "";

    const normalizeGrades = (gs) =>
      gs
        .filter((g) => g.name)
        .map((g) => ({
          name: g.name,
          price:
            g.price !== "" && g.price !== null && g.price !== undefined
              ? parseFloat(g.price)
              : null,
        }));

    const grades = (() => {
      // If grades sub-row is open, read from Alpine; else from dataset
      if (openGradesRowId === rowId) {
        const gradesDiv = document.querySelector(`#${rowId}-grades [x-data]`);
        try {
          return normalizeGrades(Alpine.$data(gradesDiv).grades);
        } catch (_) {}
      }
      return normalizeGrades(JSON.parse(tr.dataset.grades || "[]"));
    })();

    const links = (() => {
      if (openLinksRowId === rowId) {
        const linksDiv = document.querySelector(`#${rowId}-links [x-data]`);
        try {
          return Alpine.$data(linksDiv).links.filter((l) => l.trim());
        } catch (_) {}
      }
      return JSON.parse(tr.dataset.links || "[]").filter((l) => l.trim());
    })();

    const leVal = ts["limited_edition"]?.getValue();

    const getMultiOptions = (instance) =>
      (instance?.getValue() ?? []).map((v) => {
        const opt = instance.options[v] || {};
        const item = { value: v, text: opt.text || v };
        if (opt.category) item.category = opt.category;
        return item;
      });

    return {
      name: field("name"),
      acquisition_type: ts["acquisition_type"]?.getValue() ?? "",
      front_image_guid: state?.frontImageGuid ?? null,
      back_image_guid: state?.backImageGuid ?? null,
      currency_id: parseInt(
        ts["currency_id"]?.getValue() ?? REF.defaultCurrencyId,
      ),
      shop_names: ts.shops?.getValue() ?? [],
      tag_names: ts.tags?.getValue() ?? [],
      artist_names: ts.artists?.getValue() ?? [],
      pin_set_names: ts.pinSets?.getValue() ?? [],
      shop_options: getMultiOptions(ts.shops),
      tag_options: getMultiOptions(ts.tags),
      artist_options: getMultiOptions(ts.artists),
      pin_set_options: getMultiOptions(ts.pinSets),
      grades,
      links,
      limited_edition:
        leVal === "true" ? true : leVal === "false" ? false : null,
      number_produced: field("number_produced")
        ? parseInt(field("number_produced"))
        : null,
      release_date: field("release_date") || null,
      end_date: field("end_date") || null,
      funding_type: ts["funding_type"]?.getValue() || null,
      posts: parseInt(field("posts") || "1"),
      width: field("width") || null,
      height: field("height") || null,
      description: field("description") || null,
    };
  }

  // ---------------------------------------------------------------------------
  // Validation
  // ---------------------------------------------------------------------------

  function validateRow(rowId) {
    const data = collectRowData(rowId);
    const errors = [];
    if (!data.name.trim()) errors.push("Name required");
    if (!data.front_image_guid) errors.push("Front image required");
    if (!data.acquisition_type) errors.push("Acquisition type required");
    if (!data.grades.length) errors.push("At least one grade required");

    const tr = document.getElementById(rowId);
    if (errors.length) {
      tr.classList.add("row-error");
      tr.title = errors.join("; ");
    } else {
      tr.classList.remove("row-error");
      tr.title = "";
    }
    return errors.length === 0;
  }

  // ---------------------------------------------------------------------------
  // Submit
  // ---------------------------------------------------------------------------

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

  async function submitAll() {
    // Close any open sub-rows so their data is saved to dataset
    if (openGradesRowId) closeGrades(openGradesRowId);
    if (openLinksRowId) closeLinks(openLinksRowId);

    const rows = document.querySelectorAll("#bulk-tbody > tr.bulk-data-row");
    if (!rows.length) return;

    let allValid = true;
    rows.forEach((tr) => {
      if (!validateRow(tr.dataset.rowId)) allValid = false;
    });
    if (!allValid) return;

    const pins = Array.from(rows).map((tr) => collectRowData(tr.dataset.rowId));

    const submitBtn = document.getElementById("submit-btn");
    submitBtn.disabled = true;
    setLucideIcon(submitBtn, "loader-circle");

    try {
      const res = await fetch(REF.submitUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pins }),
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(`Server error ${res.status}: ${detail}`);
      }
      const result = await res.json();
      handleSubmitResult(result, rows);
    } catch (err) {
      console.error("Submit failed", err);
      alert("Submit failed: " + err.message);
    } finally {
      submitBtn.disabled = false;
      setLucideIcon(submitBtn, "upload");
    }
  }

  function handleSubmitResult(result, rows) {
    const rowArr = Array.from(rows);

    // Mark errors on failed rows (in reverse so indices stay valid as we remove)
    const failedIndices = new Set();
    result.results.forEach((r) => {
      if (!r.success) {
        failedIndices.add(r.index);
        const tr = rowArr[r.index];
        if (tr) {
          tr.classList.add("row-error");
          tr.title = r.error || "Unknown error";
        }
      }
    });

    if (result.failed_count === 0) {
      // All succeeded — clear table
      Array.from(document.querySelectorAll("#bulk-tbody > tr")).forEach((tr) =>
        tr.remove(),
      );
      rowTS.forEach((ts) => Object.values(ts).forEach((i) => i?.destroy?.()));
      rowTS.clear();
      rowState.clear();
      updateSubmitLabel();
    } else {
      // Remove only successful rows
      result.results.forEach((r, i) => {
        if (r.success) {
          const tr = rowArr[r.index];
          if (tr) deleteRow(tr.dataset.rowId);
        }
      });
    }

    showSuccessModal(result);
  }

  // ---------------------------------------------------------------------------
  // Success modal
  // ---------------------------------------------------------------------------

  function showSuccessModal(result) {
    const modal = document.getElementById("success-modal");
    const grid = document.getElementById("modal-grid");
    const title = document.getElementById("modal-title");

    title.textContent = `${result.created_count} pin${result.created_count !== 1 ? "s" : ""} imported${result.failed_count ? `, ${result.failed_count} failed` : ""}`;

    grid.innerHTML = "";
    result.results
      .filter((r) => r.success)
      .forEach((r) => {
        const card = document.createElement("a");
        card.href = `/get/pin/${r.pin_id}`;
        card.className =
          "flex flex-col gap-1 items-center border border-pin-border rounded-lg p-2 hover:border-accent no-underline text-pin-base-text text-center";
        card.innerHTML = `
          <div style="width:100%;aspect-ratio:1;background:url('/get/image/${r.front_image_guid}?thumbnail=true') center/cover no-repeat;border-radius:6px;"></div>
          <span class="text-xs truncate w-full text-center">${escHtml(r.pin_name || "")}</span>
        `;
        grid.appendChild(card);
      });

    if (result.failed_count > 0) {
      const errTitle = document.createElement("p");
      errTitle.className = "col-span-full text-sm text-red-200 font-semibold";
      errTitle.textContent =
        "Failed rows remain in the table — fix errors and resubmit.";
      grid.appendChild(errTitle);
    }

    modal.classList.remove("hidden");
  }

  function closeModal() {
    document.getElementById("success-modal").classList.add("hidden");
  }

  // ---------------------------------------------------------------------------
  // Name column auto-width
  // ---------------------------------------------------------------------------

  /**
   * Expands the name column to fit the longest current value (min 15ch).
   * Called on every input event for name fields.
   */
  function syncNameColWidth() {
    let maxChars = 15;
    document.querySelectorAll('input[data-field="name"]').forEach((inp) => {
      if (inp.value.length > maxChars) maxChars = inp.value.length;
    });
    const minW = maxChars + 2 + "ch";
    document.querySelectorAll('[data-col-type="name"]').forEach((el) => {
      el.style.minWidth = minW;
    });
  }

  // ---------------------------------------------------------------------------
  // Local option broadcasting
  // ---------------------------------------------------------------------------

  /**
   * When a user creates a new option in one row's TS instance, broadcast it to
   * all other existing instances of the same entity type so they can find it.
   */
  function broadcastLocalOption(entityType, value, item, sourceRowId, sourceField) {
    const fieldByType = {
      shop: "shops",
      tag: "tags",
      artist: "artists",
      pin_set: "pinSets",
    };
    const tsField = fieldByType[entityType];
    if (!tsField) return;
    rowTS.forEach((tsMap, rowId) => {
      if (rowId === sourceRowId) return; // already has it (just created)
      const instance = tsMap[tsField];
      if (instance && !instance.options[value]) {
        instance.addOption(item);
      }
    });
  }

  // ---------------------------------------------------------------------------
  // Utilities
  // ---------------------------------------------------------------------------

  function escHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }
})();
