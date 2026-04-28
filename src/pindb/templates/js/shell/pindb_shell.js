(function () {
  function pindbAfterVendorScripts() {
    var element = document.getElementById("back-link");
    if (element != null) {
      var storageKey = "pin_back:" + window.location.pathname;
      var params = new URLSearchParams(window.location.search);
      var backUrl = params.get("back");
      if (backUrl) {
        sessionStorage.setItem(storageKey, backUrl);
        element.setAttribute("href", backUrl);
      } else {
        var stored = sessionStorage.getItem(storageKey);
        if (stored) {
          element.setAttribute("href", stored);
        } else {
          element.setAttribute("href", document.referrer || "#");
          element.onclick = function () {
            history.back();
            return false;
          };
        }
      }
    }
    window.pindbNotyf = new Notyf({
      dismissible: true,
      duration: 4500,
      position: { x: "right", y: "bottom" },
      ripple: true,
    });
    document.addEventListener("pindbToast", function (evt) {
      var d = evt.detail;
      if (!d || typeof d !== "object") {
        return;
      }
      var msg = d.message;
      if (!msg) {
        return;
      }
      var typ = d.type || "success";
      if (typ === "success") {
        window.pindbNotyf.success(msg);
      } else {
        window.pindbNotyf.error(msg);
      }
    });
    document.body.addEventListener("htmx:afterSwap", function (evt) {
      lucide.createIcons();
      var target = evt.detail.target;
      if (!target || target.id !== "pindb-toast-host") {
        return;
      }
      var sig = target.querySelector("#pindb-toast-signal");
      if (!sig) {
        return;
      }
      var msg = sig.dataset.pindbMessage;
      if (!msg) {
        target.innerHTML = "";
        return;
      }
      var typ = sig.dataset.pindbType || "error";
      if (typ === "success") {
        window.pindbNotyf.success(msg);
      } else {
        window.pindbNotyf.error(msg);
      }
      target.innerHTML = "";
    });
    if (window.lucide) {
      lucide.createIcons();
    }
    document.addEventListener(
      "mousemove",
      function (evt) {
        var card = evt.target.closest && evt.target.closest(".pin-3d-card");
        if (!card) return;
        var r = card.getBoundingClientRect();
        var x = (evt.clientX - r.left) / r.width;
        var y = (evt.clientY - r.top) / r.height;
        card.style.setProperty("--gx", (x * 100).toFixed(2) + "%");
        card.style.setProperty("--gy", (y * 100).toFixed(2) + "%");
        card.style.setProperty("--rx", ((0.5 - y) * 5).toFixed(2) + "deg");
        card.style.setProperty("--ry", ((x - 0.5) * 5).toFixed(2) + "deg");
      },
      { passive: true },
    );
    document.addEventListener("mouseout", function (evt) {
      var card = evt.target.closest && evt.target.closest(".pin-3d-card");
      if (!card) return;
      if (evt.relatedTarget && card.contains(evt.relatedTarget)) return;
      card.style.removeProperty("--rx");
      card.style.removeProperty("--ry");
    });
    document.querySelectorAll("time[data-localtime]").forEach(function (el) {
      var iso = el.getAttribute("datetime");
      if (!iso) return;
      try {
        el.textContent = new Date(iso).toLocaleDateString();
      } catch {}
    });
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", pindbAfterVendorScripts);
  } else {
    pindbAfterVendorScripts();
  }
})();
