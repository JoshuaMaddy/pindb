(function () {
  var MIN = 0.5,
    MAX = 3.0,
    STEP = 0.1;
  var overlay,
    imgEl,
    label,
    openerEl,
    scale = 1,
    tx = 0,
    ty = 0;
  var pointers = new Map(),
    pinchStart = 0,
    scaleStart = 1;
  var dragging = false,
    dragStartX = 0,
    dragStartY = 0,
    txStart = 0,
    tyStart = 0;

  function clamp(v, lo, hi) {
    return Math.max(lo, Math.min(hi, v));
  }

  function applyTransform() {
    if (scale <= 1) {
      tx = 0;
      ty = 0;
    }
    imgEl.style.transform =
      "translate(" + tx + "px," + ty + "px) scale(" + scale + ")";
    label.textContent = Math.round(scale * 100) + "%";
    imgEl.style.cursor = scale > 1 ? "grab" : "default";
  }

  function setScale(next, cx, cy) {
    var prev = scale;
    next = clamp(next, MIN, MAX);
    if (next === prev) return;
    if (cx != null && cy != null) {
      var rect = imgEl.getBoundingClientRect();
      var ox = cx - (rect.left + rect.width / 2);
      var oy = cy - (rect.top + rect.height / 2);
      var ratio = next / prev;
      tx = (tx - ox) * ratio + ox;
      ty = (ty - oy) * ratio + oy;
    }
    scale = next;
    applyTransform();
  }

  function trapFocus(evt) {
    if (evt.key !== "Tab") return;
    var f = overlay.querySelectorAll('button, [tabindex="0"]');
    if (!f.length) return;
    var first = f[0],
      last = f[f.length - 1];
    if (evt.shiftKey && document.activeElement === first) {
      evt.preventDefault();
      last.focus();
    } else if (!evt.shiftKey && document.activeElement === last) {
      evt.preventDefault();
      first.focus();
    }
  }

  function onKey(evt) {
    if (overlay.classList.contains("hidden")) return;
    if (evt.key === "Escape") {
      close();
    } else if (evt.key === "+" || evt.key === "=") {
      setScale(scale + STEP);
    } else if (evt.key === "-" || evt.key === "_") {
      setScale(scale - STEP);
    } else if (evt.key === "0") {
      scale = 1;
      tx = 0;
      ty = 0;
      applyTransform();
    } else {
      trapFocus(evt);
    }
  }

  function open(src, alt, opener) {
    imgEl.src = src;
    imgEl.alt = alt || "";
    scale = 1;
    tx = 0;
    ty = 0;
    applyTransform();
    overlay.classList.remove("hidden");
    overlay.classList.add("flex");
    document.body.style.overflow = "hidden";
    openerEl = opener || document.activeElement;
    var closeBtn = overlay.querySelector("#pin-lightbox-close");
    if (closeBtn) closeBtn.focus();
  }

  function close() {
    overlay.classList.add("hidden");
    overlay.classList.remove("flex");
    document.body.style.overflow = "";
    imgEl.removeAttribute("src");
    if (openerEl && openerEl.focus) openerEl.focus();
    openerEl = null;
  }

  function onWheel(evt) {
    evt.preventDefault();
    var delta = evt.deltaY < 0 ? STEP : -STEP;
    setScale(scale + delta, evt.clientX, evt.clientY);
  }

  function onPointerDown(evt) {
    pointers.set(evt.pointerId, { x: evt.clientX, y: evt.clientY });
    if (pointers.size === 2) {
      var pts = Array.from(pointers.values());
      pinchStart = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
      scaleStart = scale;
    } else if (pointers.size === 1 && scale > 1) {
      dragging = true;
      dragStartX = evt.clientX;
      dragStartY = evt.clientY;
      txStart = tx;
      tyStart = ty;
      imgEl.style.cursor = "grabbing";
      imgEl.setPointerCapture(evt.pointerId);
    }
  }

  function onPointerMove(evt) {
    if (!pointers.has(evt.pointerId)) return;
    pointers.set(evt.pointerId, { x: evt.clientX, y: evt.clientY });
    if (pointers.size === 2 && pinchStart > 0) {
      var pts = Array.from(pointers.values());
      var dist = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
      var cx = (pts[0].x + pts[1].x) / 2;
      var cy = (pts[0].y + pts[1].y) / 2;
      setScale(scaleStart * (dist / pinchStart), cx, cy);
    } else if (dragging) {
      tx = txStart + (evt.clientX - dragStartX);
      ty = tyStart + (evt.clientY - dragStartY);
      applyTransform();
    }
  }

  function onPointerUp(evt) {
    pointers.delete(evt.pointerId);
    if (pointers.size < 2) pinchStart = 0;
    if (pointers.size === 0) {
      dragging = false;
      imgEl.style.cursor = scale > 1 ? "grab" : "default";
    }
  }

  function onOverlayClick(evt) {
    if (evt.target === overlay) close();
  }

  function init() {
    overlay = document.getElementById("pin-lightbox");
    if (!overlay) return;
    if (overlay.parentNode !== document.body) document.body.appendChild(overlay);
    imgEl = document.getElementById("pin-lightbox-img");
    label = document.getElementById("pin-lightbox-zoom-label");
    overlay.addEventListener("click", onOverlayClick);
    overlay.querySelector("#pin-lightbox-close").addEventListener("click", close);
    overlay
      .querySelector("#pin-lightbox-zoom-in")
      .addEventListener("click", function () {
        setScale(scale + STEP);
      });
    overlay
      .querySelector("#pin-lightbox-zoom-out")
      .addEventListener("click", function () {
        setScale(scale - STEP);
      });
    imgEl.addEventListener("wheel", onWheel, { passive: false });
    imgEl.addEventListener("pointerdown", onPointerDown);
    imgEl.addEventListener("pointermove", onPointerMove);
    imgEl.addEventListener("pointerup", onPointerUp);
    imgEl.addEventListener("pointercancel", onPointerUp);
    document.addEventListener("keydown", onKey);

    document.addEventListener("click", function (evt) {
      var t = evt.target.closest && evt.target.closest(".pin-zoomable");
      if (!t) return;
      evt.preventDefault();
      open(t.dataset.full || t.src, t.alt, t);
    });
    document.addEventListener("keydown", function (evt) {
      if (evt.key !== "Enter" && evt.key !== " ") return;
      var t = evt.target.closest && evt.target.closest(".pin-zoomable");
      if (!t) return;
      evt.preventDefault();
      open(t.dataset.full || t.src, t.alt, t);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
