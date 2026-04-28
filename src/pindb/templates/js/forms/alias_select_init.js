document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("select.alias-select").forEach(function (el) {
    new TomSelect(el, {
      maxItems: null,
      create: true,
      persist: false,
      plugins: ["remove_button"],
    });
  });
});
