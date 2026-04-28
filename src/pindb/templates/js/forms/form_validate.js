(function () {
  const FIELD_LABELS = {
    grade_names: "Grade name",
    grade_prices: "Grade price",
    front_image: "Front image",
    back_image: "Back image",
    shop_ids: "Shop",
    tag_ids: "Tag",
    artist_ids: "Artist",
    pin_sets_ids: "Pin set",
    acquisition_type: "Acquisition",
    currency_id: "Currency",
  };

  function humanize(name) {
    if (!name) return "Field";
    if (FIELD_LABELS[name]) return FIELD_LABELS[name];
    return name
      .replace(/_/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());
  }

  function labelFor(el) {
    if (el.dataset && el.dataset.label) return el.dataset.label;
    if (el.id) {
      const lbl = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (lbl) {
        return lbl.textContent.replace(/\*+\s*$/, "").trim() || humanize(el.name);
      }
    }
    const parentLabel = el.closest("label");
    if (parentLabel) {
      return parentLabel.textContent.replace(/\*+\s*$/, "").trim() || humanize(el.name);
    }
    return humanize(el.name);
  }

  function valueMissing(el) {
    if (el.disabled) return false;
    if (el.type === "file") {
      return !el.files || el.files.length === 0;
    }
    if (el.tagName === "SELECT") {
      if (el.multiple) {
        return Array.from(el.selectedOptions).length === 0;
      }
      return !el.value;
    }
    if (el.type === "checkbox" || el.type === "radio") {
      return !el.checked;
    }
    return !(el.value || "").trim();
  }

  function validateForm(form) {
    const seen = new Set();
    const errors = [];
    form.querySelectorAll("[required]").forEach((el) => {
      if (el.disabled) return;
      // x-template clones inside <template> are inert; only validate live nodes.
      if (el.closest("template")) return;
      if (!valueMissing(el)) return;
      const label = labelFor(el);
      if (seen.has(label)) return;
      seen.add(label);
      errors.push(`${label} is required.`);
    });
    return errors;
  }

  function fireToast(message) {
    document.dispatchEvent(
      new CustomEvent("pindbToast", {
        detail: { message, type: "error" },
      })
    );
  }

  function handle(evt) {
    const elt = evt.detail && evt.detail.elt;
    if (!elt || elt.tagName !== "FORM") return;
    const errors = validateForm(elt);
    if (errors.length === 0) return;
    evt.preventDefault();
    fireToast(errors[0]);
  }

  document.body.addEventListener("htmx:beforeRequest", handle);

  // Non-htmx submissions (forms with method=post, no hx-post). Browser native
  // required handling typically blocks these, but mirror server-side messaging
  // for forms whose required fields are TomSelect-hidden (browser refuses to
  // surface a tooltip on display:none controls).
  document.body.addEventListener(
    "submit",
    function (evt) {
      const form = evt.target;
      if (!form || form.tagName !== "FORM") return;
      // htmx forms are handled by htmx:beforeRequest above; skip native pass.
      if (
        form.hasAttribute("hx-post") ||
        form.hasAttribute("hx-put") ||
        form.hasAttribute("hx-patch") ||
        form.hasAttribute("hx-delete")
      ) {
        return;
      }
      const errors = validateForm(form);
      if (errors.length === 0) return;
      evt.preventDefault();
      fireToast(errors[0]);
    },
    true
  );
})();
