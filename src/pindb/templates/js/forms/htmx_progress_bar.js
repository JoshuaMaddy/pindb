// Global thin top progress bar for HTMX swaps.
//
// HTMX list controls (pagination, sort, view toggle, search), the pin search
// page, and detail-page panels all swap content with no visible feedback — a
// blank flash on slow networks. This wires one bar to the HTMX request
// lifecycle on `document.body`, so every swap shows progress without each
// control having to opt in via `hx-indicator`.
//
// Requests are ref-counted, so overlapping swaps keep the bar up until the
// last one settles. A short show-delay avoids flashing on instant swaps.
(function () {
  "use strict";

  var bar = document.getElementById("pindb-htmx-progress");
  if (!bar) return;

  var SHOW_DELAY_MS = 120;
  var active = 0;
  var showTimer = null;
  var hideTimer = null;

  function set(styles) {
    for (var key in styles) bar.style[key] = styles[key];
  }

  set({
    position: "fixed",
    top: "0",
    left: "0",
    height: "2px",
    width: "0",
    zIndex: "60",
    backgroundColor: "var(--color-accent, #89dceb)",
    opacity: "0",
    pointerEvents: "none",
    transition: "width 200ms ease-out, opacity 250ms ease-out",
    willChange: "width, opacity",
  });

  function show() {
    set({ opacity: "1", width: "0" });
    // Two frames so the browser registers width:0 before transitioning to 75%.
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        bar.style.width = "75%";
      });
    });
  }

  function start() {
    active += 1;
    if (active > 1) return;
    if (hideTimer) {
      clearTimeout(hideTimer);
      hideTimer = null;
    }
    showTimer = setTimeout(show, SHOW_DELAY_MS);
  }

  function done() {
    active = Math.max(0, active - 1);
    if (active > 0) return;
    if (showTimer) {
      clearTimeout(showTimer);
      showTimer = null;
    }
    // If the request finished before the show-delay elapsed, nothing was shown.
    if (bar.style.opacity === "0") return;
    bar.style.width = "100%";
    hideTimer = setTimeout(function () {
      bar.style.opacity = "0";
      hideTimer = setTimeout(function () {
        bar.style.width = "0";
      }, 250);
    }, 200);
  }

  document.body.addEventListener("htmx:beforeRequest", start);
  document.body.addEventListener("htmx:afterRequest", done);
})();
