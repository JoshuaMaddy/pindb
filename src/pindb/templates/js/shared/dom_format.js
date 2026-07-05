// =============================================================================
// PinDB shared DOM/formatting helpers
//
// Loaded (deferred, before its consumers) by the bulk import and bulk tag
// pages, which both need to swap a Lucide icon in place and HTML-escape text
// for innerHTML. Single source of truth for both.
// =============================================================================

(function () {
  "use strict";

  /**
   * Replace (or prepend) a Lucide `<i data-lucide>` placeholder inside
   * `container` and re-render icons within that container.
   *
   * @param {Element} container
   * @param {string} iconName
   */
  globalThis.pindbSetLucideIcon = function (container, iconName) {
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
  };

  /**
   * Escape `&`, `<`, and `>` for safe interpolation into innerHTML.
   *
   * @param {unknown} str
   * @returns {string}
   */
  globalThis.pindbEscHtml = function (str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  };
})();
