/**
 * Disables submit control(s) and shows a spinner while an HTMX request is in
 * flight for forms marked with `data-htmx-submit-guard`. Blocks duplicate
 * submissions. Restores on error; leaves as-is on `HX-Redirect` (navigation).
 */
(function () {
  "use strict";

  var SPINNER_SVG =
    '<svg class="inline-block h-4 w-4 shrink-0 animate-spin" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">' +
    '<circle cx="8" cy="8" r="7" stroke="currentColor" stroke-opacity="0.25" stroke-width="2" vector-effect="non-scaling-stroke" fill="none"></circle>' +
    '<path d="M15 8a7 7 0 00-7-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" vector-effect="non-scaling-stroke" fill="none"></path>' +
    "</svg>";

  var inFlight = new WeakMap();

  function guardedFormFromElt(elt) {
    if (!elt) return null;
    var tag = elt.tagName && elt.tagName.toLowerCase();
    if (tag === "form" && elt.hasAttribute("data-htmx-submit-guard")) return elt;
    if (typeof elt.closest === "function") {
      return elt.closest("form[data-htmx-submit-guard]");
    }
    return null;
  }

  function getSubmits(form) {
    return form.querySelectorAll('button[type="submit"], input[type="submit"]');
  }

  function enterSubmitting(control) {
    control.disabled = true;
    if (control.tagName === "INPUT" && control.type === "submit") {
      if (!Object.prototype.hasOwnProperty.call(control.dataset, "htmxSubmitDefaultValue")) {
        control.dataset.htmxSubmitDefaultValue = control.value;
      }
      control.value = "Submitting…";
      return;
    }
    if (!Object.prototype.hasOwnProperty.call(control.dataset, "htmxSubmitDefaultHtml")) {
      control.dataset.htmxSubmitDefaultHtml = control.innerHTML;
    }
    control.innerHTML =
      '<span class="inline-flex items-center justify-center gap-2">' +
      "<span>Submitting</span>" +
      SPINNER_SVG +
      "</span>";
  }

  function leaveSubmitting(control) {
    control.disabled = false;
    if (control.tagName === "INPUT" && control.type === "submit") {
      if (Object.prototype.hasOwnProperty.call(control.dataset, "htmxSubmitDefaultValue")) {
        control.value = control.dataset.htmxSubmitDefaultValue;
      }
      return;
    }
    if (Object.prototype.hasOwnProperty.call(control.dataset, "htmxSubmitDefaultHtml")) {
      control.innerHTML = control.dataset.htmxSubmitDefaultHtml;
    }
  }

  function restoreForm(form) {
    inFlight.delete(form);
    getSubmits(form).forEach(leaveSubmitting);
    form.dispatchEvent(new Event("input", { bubbles: true }));
  }

  document.body.addEventListener("htmx:beforeRequest", function (evt) {
    var form = guardedFormFromElt(evt.detail && evt.detail.elt);
    if (!form) return;
    if (evt.defaultPrevented) return;
    if (inFlight.get(form)) {
      evt.preventDefault();
      return;
    }
    inFlight.set(form, true);
    getSubmits(form).forEach(enterSubmitting);
  });

  document.body.addEventListener("htmx:afterRequest", function (evt) {
    var form = guardedFormFromElt(evt.detail && evt.detail.elt);
    if (!form || !inFlight.get(form)) return;
    var xhr = evt.detail.xhr;
    if (
      xhr &&
      typeof xhr.getResponseHeader === "function" &&
      xhr.getResponseHeader("HX-Redirect")
    ) {
      return;
    }
    restoreForm(form);
  });
})();
