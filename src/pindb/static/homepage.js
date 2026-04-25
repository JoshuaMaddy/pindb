/* Homepage redesign: cursor glow tracking + masonry seamless loop with
 * per-column animation duration so every column scrolls at the same
 * pixels-per-second regardless of its content height. */

(function () {
  "use strict";

  // Target scroll speed in pixels per second. Lower = slower.
  var PIXELS_PER_SECOND = 18;

  function init() {
    var root = document.documentElement;

    // Cursor glow tracking, rAF-throttled.
    var px = 0;
    var py = 0;
    var pending = false;
    function flush() {
      pending = false;
      root.style.setProperty("--glow-x", px + "px");
      root.style.setProperty("--glow-y", py + "px");
    }
    document.addEventListener(
      "pointermove",
      function (e) {
        px = e.clientX;
        py = e.clientY;
        if (!pending) {
          pending = true;
          requestAnimationFrame(flush);
        }
      },
      { passive: true }
    );

    // Duplicate each column's children once so the keyframe loop between
    // translateY(-50%) and translateY(0) lands on an identical second copy.
    var columns = Array.prototype.slice.call(
      document.querySelectorAll(".masonry-col-inner")
    );
    columns.forEach(function (inner) {
      inner.innerHTML = inner.innerHTML + inner.innerHTML;
    });

    // Per-column phase offset (fraction of the loop, 0–1). Hand-tuned so the
     // tops of adjacent columns never align, breaking the grid feel.
    var PHASE_OFFSETS = [0.0, 0.42, 0.18, 0.71, 0.31, 0.59, 0.08];

    // Set per-column animation duration so pixels-per-second is constant,
    // and a negative animation-delay so columns start at different phases.
    function applyDurations() {
      columns.forEach(function (inner, idx) {
        // The keyframe travels 50% of the duplicated height, which equals
        // exactly one original copy's height.
        var travel = inner.scrollHeight / 2;
        if (travel < 1) return;
        var seconds = travel / PIXELS_PER_SECOND;
        var phase = PHASE_OFFSETS[idx % PHASE_OFFSETS.length];
        inner.style.animationDuration = seconds.toFixed(2) + "s";
        inner.style.animationDelay = "-" + (seconds * phase).toFixed(2) + "s";
      });
    }

    applyDurations();

    // Re-measure once images finish loading (heights change as images decode).
    var imgs = document.querySelectorAll(".masonry-pin-img");
    var remaining = imgs.length;
    if (remaining === 0) return;
    function done() {
      remaining -= 1;
      if (remaining <= 0) applyDurations();
    }
    imgs.forEach(function (img) {
      if (img.complete && img.naturalWidth > 0) {
        done();
      } else {
        img.addEventListener("load", done, { once: true });
        img.addEventListener("error", done, { once: true });
      }
    });

    // Also re-measure on resize (column widths change → image heights change).
    var resizeTimer = null;
    window.addEventListener("resize", function () {
      if (resizeTimer) clearTimeout(resizeTimer);
      resizeTimer = setTimeout(applyDurations, 150);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
