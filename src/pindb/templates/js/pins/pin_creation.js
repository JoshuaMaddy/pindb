// Pin form wiring: limited-edition toggle and the required-field submit
// gate. Select widgets are Svelte `multi-select` islands (they adopt the
// server-rendered selects and dispatch real change events on them); image
// drop/paste/preview + WebP transcode live in the `pin-images` island.
window.addEventListener("load", function () {
  var _refEl = document.getElementById("pin-form-ref-data");
  if (_refEl && _refEl.textContent && !window.PIN_FORM_REF) {
    try {
      window.PIN_FORM_REF = JSON.parse(_refEl.textContent);
    } catch {}
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

  function acquisitionOk() {
    const el = document.getElementById("acquisition_type");
    return !!(el && el.value);
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
    shops: () => globalThis.pindbSelectHasItems("shop_ids"),
    acquisition: acquisitionOk,
    grades: gradesOk,
    tags: () => globalThis.pindbSelectHasItems("tag_ids"),
  };

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
    // The island moves the select inside its widget root — highlight that.
    return sel.closest("[data-multiselect]") || sel;
  }

  const gate = globalThis.pindbCreateFormGate({
    form: form,
    submitBtn: submitBtn,
    fieldOrder: FIELD_ORDER,
    checks: checks,
    hintText: HINT_TEXT,
    findHighlightEl: findHighlightEl,
    hintSelector: ".pin-form-field-hint",
    // Right-column fields use the inner label|field grid: pin hint under field
    // only, leaving column 1 empty (front image lives in the outer left column).
    hintClassFor: (key) =>
      key === "front"
        ? "pin-form-field-hint text-error-main text-sm mt-1"
        : "pin-form-field-hint text-error-main text-sm mt-1 max-sm:col-span-full sm:col-start-2",
  });

  // Select widget islands dispatch bubbling change events on the adopted
  // selects, which the gate's form-level change listener already sees.
  const frontInp = document.getElementById("front_image");
  if (frontInp) {
    frontInp.addEventListener("change", gate.refresh);
  }
}
