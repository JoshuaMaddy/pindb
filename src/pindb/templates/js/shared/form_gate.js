// =============================================================================
// PinDB shared required-field form gate
//
// Disables a submit button (visually + aria) until required fields pass, and
// after a failed submit shows inline hints next to the offending fields. The
// machinery is identical across the pin create/edit form and the simple
// entity forms (shop/artist/tag/pin set); callers supply only the per-form
// config. Loaded (deferred) before its consumers.
// =============================================================================

(function () {
  "use strict";

  var ERR_CLASSES = [
    "ring-2",
    "ring-error-main",
    "rounded-md",
    "border",
    "border-error-main",
    "p-1",
  ];

  /**
   * True when the select for `selectId` has at least one selected value.
   * Widget-agnostic: both the Svelte multi-select island and (historically)
   * Tom Select keep the underlying select element's selection in sync.
   * @param {string} selectId
   * @returns {boolean}
   */
  globalThis.pindbSelectHasItems = function (selectId) {
    var el = document.getElementById(selectId);
    if (!el) return false;
    if (el.multiple) return el.selectedOptions.length > 0;
    return el.value !== "" && el.value !== null && el.value !== undefined;
  };

  /**
   * Wire a required-field gate onto a form.
   *
   * @param {Object} cfg
   * @param {HTMLElement} cfg.form
   * @param {HTMLElement} cfg.submitBtn
   * @param {string[]} cfg.fieldOrder            ordered field keys
   * @param {Record<string, () => boolean>} cfg.checks   key -> "is satisfied"
   * @param {Record<string, string>} cfg.hintText        key -> hint message
   * @param {(key: string) => Element | null} cfg.findHighlightEl
   * @param {string} cfg.hintSelector            selector matching inserted hints
   * @param {(key: string) => string} cfg.hintClassFor   class string per hint
   * @returns {{ refresh: () => void }}  call `refresh` after external changes
   *   (e.g. Tom Select / file input change events the form doesn't bubble).
   */
  globalThis.pindbCreateFormGate = function (cfg) {
    var form = cfg.form;
    var submitBtn = cfg.submitBtn;
    var FIELD_ORDER = cfg.fieldOrder;
    var checks = cfg.checks;
    var hintsShown = false;

    function computeValid() {
      return FIELD_ORDER.every(function (k) {
        return checks[k]();
      });
    }

    function removeHints() {
      document.querySelectorAll(cfg.hintSelector).forEach(function (n) {
        n.remove();
      });
    }

    function clearErrorDecorations() {
      removeHints();
      FIELD_ORDER.forEach(function (key) {
        var el = cfg.findHighlightEl(key);
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
        var target = cfg.findHighlightEl(key);
        if (!target) return;
        ERR_CLASSES.forEach(function (c) {
          target.classList.add(c);
        });
        var hint = document.createElement("p");
        hint.className = cfg.hintClassFor(key);
        hint.setAttribute("role", "alert");
        hint.textContent = cfg.hintText[key];
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
        var el = cfg.findHighlightEl(key);
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

    form.addEventListener("input", refreshAfterHintsGate);
    form.addEventListener("change", refreshAfterHintsGate, true);

    updateSubmitAppearance();

    return { refresh: refreshAfterHintsGate };
  };
})();
