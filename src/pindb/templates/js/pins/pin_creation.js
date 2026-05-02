/** libwebp WASM via bundled @jsquash/webp (see scripts/build-webp-encode.mjs). */
var PIN_IMAGE_WEBP_QUALITY = 95;

/**
 * Replace raster file inputs with WebP when `globalThis.pindbWebpFromFile` is
 * available (module loaded). On failure or missing encoder, leaves the file
 * unchanged.
 *
 * @param {HTMLInputElement | null} input
 * @returns {Promise<void>}
 */
async function maybeTranscodePinImageToWebp(input) {
  if (!input || !input.files || input.files.length === 0) return;
  var file = input.files[0];
  if (file.type === "image/webp") return;
  if (file.type && file.type.indexOf("image/") !== 0) return;
  var enc = globalThis.pindbWebpFromFile;
  if (typeof enc !== "function") return;
  try {
    var blob = await enc(file, PIN_IMAGE_WEBP_QUALITY);
    if (!blob || blob.size === 0) return;
    var stem = file.name.replace(/\.[^.\\/]+$/, "") || "image";
    var webpFile = new File([blob], stem + ".webp", {
      type: "image/webp",
      lastModified: Date.now(),
    });
    var dt = new DataTransfer();
    dt.items.add(webpFile);
    input.files = dt.files;
  } catch {
    /* keep original */
  }
}

window.addEventListener("load", function () {
  var _refEl = document.getElementById("pin-form-ref-data");
  if (_refEl && _refEl.textContent && !window.PIN_FORM_REF) {
    try {
      window.PIN_FORM_REF = JSON.parse(_refEl.textContent);
    } catch {}
  }

  // -------------------------------
  // Tom Select Initialization
  // -------------------------------

  const _PIN_FORM_REF = window.PIN_FORM_REF;

  const _noResultsRender = {
    no_results: (data) => {
      const msg =
        data.input && data.input.length > 0
          ? "No results found"
          : "Start typing to search…";
      return `<div class="no-results">${msg}</div>`;
    },
  };

  document.querySelectorAll("select.multi-select").forEach((el) => {
    const entityType = el.dataset.entityType;
    if (entityType && _PIN_FORM_REF) {
      const opts = {
        load: (query, callback) => {
          let url = `${_PIN_FORM_REF.optionsBaseUrl}/${entityType}?q=${encodeURIComponent(query)}`;
          if (entityType === "pin" && _PIN_FORM_REF.excludePinId != null) {
            url += `&exclude=${encodeURIComponent(_PIN_FORM_REF.excludePinId)}`;
          }
          fetch(url)
            .then((res) => res.json())
            .then(callback)
            .catch(() => callback());
        },
        shouldLoad: (q) => q.length > 0,
        maxItems: null,
        plugins: ["caret_position", "remove_button"],
        valueField: "value",
        labelField: "text",
        searchField: "text",
        persist: true,
        render: { ..._noResultsRender },
      };
      if (entityType === "tag") {
        opts.render = {
          ..._noResultsRender,
          item: TagSelect.tagItemRender,
          option: TagSelect.tagOptionRender,
        };
        Object.assign(opts, TagSelect.tagSelectLucideCallbacks());
      } else if (entityType === "pin") {
        const pinRender = (item, escape) => {
          const thumb = item.thumbnail
            ? `<img src="${escape(item.thumbnail)}" class="w-6 h-6 object-contain rounded bg-main shrink-0 mr-2" alt="">`
            : "";
          return `<div class="flex items-center gap-1">${thumb}<span>${escape(item.text)}</span></div>`;
        };
        opts.render = {
          ..._noResultsRender,
          item: pinRender,
          option: pinRender,
        };
      }
      new TomSelect(el, opts);
    } else {
      new TomSelect(el, {
        maxItems: null,
        plugins: ["caret_position", "remove_button"],
      });
    }
  });

  document.querySelectorAll("select.single-select").forEach((el) => {
    new TomSelect(el, {});
  });

  // -------------------------------
  // Drag & Drop Upload Boxes
  // -------------------------------

  let _hoveredImageBox = null;

  document.querySelectorAll(".image-drop").forEach((box) => {
    const inputId = box.dataset.inputId;
    const input = document.getElementById(inputId);

    box.addEventListener("click", () => input.click());

    input.addEventListener("change", async () => {
      await maybeTranscodePinImageToWebp(input);
      if (input.files[0]) showPreview(box, input.files[0]);
    });

    box.addEventListener("mouseenter", () => {
      _hoveredImageBox = { box, input };
    });
    box.addEventListener("mouseleave", () => {
      _hoveredImageBox = null;
    });

    box.addEventListener("dragover", (e) => {
      e.preventDefault();
      box.classList.replace("border-lightest", "border-accent");
    });

    box.addEventListener("dragleave", () => {
      box.classList.replace("border-accent", "border-lightest");
    });

    box.addEventListener("drop", async (e) => {
      e.preventDefault();
      box.classList.remove("border-lightest");
      box.classList.add("border-accent");

      const file = e.dataTransfer.files[0];
      if (!file) return;

      const dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;

      await maybeTranscodePinImageToWebp(input);
      if (input.files[0]) showPreview(box, input.files[0]);
    });
  });

  document.addEventListener("paste", (e) => {
    if (!_hoveredImageBox) return;
    const items = e.clipboardData?.items;
    if (!items) return;
    for (const item of items) {
      if (item.type.startsWith("image/")) {
        const file = item.getAsFile();
        if (!file) continue;
        const dt = new DataTransfer();
        dt.items.add(file);
        _hoveredImageBox.input.files = dt.files;
        void (async () => {
          await maybeTranscodePinImageToWebp(_hoveredImageBox.input);
          const f = _hoveredImageBox.input.files[0];
          if (f) showPreview(_hoveredImageBox.box, f);
        })();
        e.preventDefault();
        break;
      }
    }
  });

  function showPreview(box, file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      box.style.backgroundImage = `url('${e.target.result}')`;
      box.textContent = "";
    };
    reader.readAsDataURL(file);
  }

  // -------------------------------
  // Limited Edition
  // -------------------------------

  const limitedEditionCheckbox = document.getElementById("limited_edition");
  const limitedEditionYes = document.getElementById("limited_edition_yes");
  const limitedEditionNo = document.getElementById("limited_edition_no");

  if (limitedEditionCheckbox && limitedEditionYes && limitedEditionNo) {
    const limitedEditionSelected = ["bg-main", "border-accent", "text-accent"];

    limitedEditionYes.addEventListener("click", (e) => {
      e.preventDefault();
      limitedEditionCheckbox.checked = true;
      limitedEditionCheckbox.value = "true";
      limitedEditionYes.classList.add(...limitedEditionSelected);
      limitedEditionNo.classList.remove(...limitedEditionSelected);
    });

    limitedEditionNo.addEventListener("click", (e) => {
      e.preventDefault();
      limitedEditionCheckbox.checked = true;
      limitedEditionCheckbox.value = "false";
      limitedEditionNo.classList.add(...limitedEditionSelected);
      limitedEditionYes.classList.remove(...limitedEditionSelected);
    });
  }

  // -------------------------------
  // Required-field gate + hints (submit UX)
  // -------------------------------

  initPinFormValidation();
});

/**
 * Disables submit visually until required fields are satisfied; if the user
 * submits while invalid, shows inline guidance (only after that attempt).
 */
function initPinFormValidation() {
  const form = document.getElementById("pin-form");
  const submitBtn = document.getElementById("pin-form-submit");
  const ref = window.PIN_FORM_REF;
  if (!form || !submitBtn || !ref) return;

  const FIELD_ORDER = [
    "name",
    "front",
    "shops",
    "acquisition",
    "grades",
    "tags",
  ];

  const HINT_TEXT = {
    name: "Enter a name for this pin.",
    front: "Upload a front image.",
    shops: "Select at least one shop.",
    acquisition: "Choose how this pin was acquired.",
    grades: "Enter at least one grade name.",
    tags: "Select at least one tag.",
  };

  const ERR_CLASSES = [
    "ring-2",
    "ring-error-main",
    "rounded-md",
    "border",
    "border-error-main",
    "p-1",
  ];

  let hintsShown = false;

  function tomSelectHasItems(selectId) {
    const el = document.getElementById(selectId);
    if (!el || !el.tomselect) return false;
    const v = el.tomselect.getValue();
    if (Array.isArray(v)) return v.length > 0;
    return v !== "" && v !== null && typeof v !== "undefined";
  }

  function acquisitionOk() {
    const el = document.getElementById("acquisition_type");
    if (!el) return false;
    if (el.tomselect) {
      const v = el.tomselect.getValue();
      return v !== "" && v !== null && typeof v !== "undefined";
    }
    return !!el.value;
  }

  function gradesOk() {
    const inputs = document.querySelectorAll(
      '#pin-form input[name="grade_names"]',
    );
    for (let i = 0; i < inputs.length; i++) {
      if (inputs[i].value.trim()) return true;
    }
    return false;
  }

  function frontOk() {
    if (!ref.requireFrontImage) return true;
    const inp = document.getElementById("front_image");
    if (inp && inp.files && inp.files.length > 0) return true;
    const prev = document.getElementById("front_image_preview");
    if (!prev) return false;
    const bg = (prev.style && prev.style.backgroundImage) || "";
    if (!bg || bg === "none") return false;
    return bg.includes("url(");
  }

  const checks = {
    name: () => {
      const el = document.getElementById("name");
      return !!(el && el.value.trim());
    },
    front: frontOk,
    shops: () => tomSelectHasItems("shop_ids"),
    acquisition: acquisitionOk,
    grades: gradesOk,
    tags: () => tomSelectHasItems("tag_ids"),
  };

  function computeValid() {
    return FIELD_ORDER.every((k) => checks[k]());
  }

  function findHighlightEl(key) {
    if (key === "name") {
      return document.querySelector('[data-pin-field="name"]');
    }
    if (key === "front") {
      return document.querySelector('[data-pin-field="front"]');
    }
    if (key === "grades") {
      return document.getElementById("pin-grade-section");
    }
    const selId =
      key === "shops"
        ? "shop_ids"
        : key === "tags"
          ? "tag_ids"
          : key === "acquisition"
            ? "acquisition_type"
            : null;
    const sel = selId ? document.getElementById(selId) : null;
    if (!sel) return null;
    return sel.tomselect ? sel.tomselect.wrapper : sel;
  }

  function removeHints() {
    document.querySelectorAll(".pin-form-field-hint").forEach((n) => n.remove());
  }

  function clearErrorDecorations() {
    removeHints();
    FIELD_ORDER.forEach((key) => {
      const el = findHighlightEl(key);
      if (!el) return;
      ERR_CLASSES.forEach((c) => el.classList.remove(c));
    });
  }

  function applyHintsForInvalid() {
    clearErrorDecorations();
    FIELD_ORDER.forEach((key) => {
      if (checks[key]()) return;
      const target = findHighlightEl(key);
      if (!target) return;
      ERR_CLASSES.forEach((c) => target.classList.add(c));
      const hint = document.createElement("p");
      /* Right-column fields use the inner label|field grid: pin hint under field only,
         leave column 1 empty on that row (front image lives in the outer left column). */
      hint.className =
        key === "front"
          ? "pin-form-field-hint text-error-main text-sm mt-1"
          : "pin-form-field-hint text-error-main text-sm mt-1 max-sm:col-span-full sm:col-start-2";
      hint.setAttribute("role", "alert");
      hint.textContent = HINT_TEXT[key];
      target.insertAdjacentElement("afterend", hint);
    });
  }

  function updateSubmitAppearance() {
    const ok = computeValid();
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
    for (let i = 0; i < FIELD_ORDER.length; i++) {
      const key = FIELD_ORDER[i];
      if (checks[key]()) continue;
      const el = findHighlightEl(key);
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

  ["shop_ids", "tag_ids", "acquisition_type"].forEach((id) => {
    const el = document.getElementById(id);
    if (el && el.tomselect) {
      el.tomselect.on("change", refreshAfterHintsGate);
    }
  });

  const frontInp = document.getElementById("front_image");
  if (frontInp) {
    frontInp.addEventListener("change", refreshAfterHintsGate);
  }

  updateSubmitAppearance();
}
