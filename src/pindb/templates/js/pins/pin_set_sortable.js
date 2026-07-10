(function () {
  // Vendored sortable.min.js loads (deferred, in document order) before this
  // script — see templates/create_and_edit/pin_set.py head_content.
  var grid = document.getElementById("pin-list");
  if (!grid || !window.Sortable) return;
  Sortable.create(grid, {
    animation: 150,
    onEnd: function () {
      var items = grid.querySelectorAll("[data-pin-id]");
      var fd = new FormData();
      items.forEach(function (el) {
        fd.append("pin_ids", el.getAttribute("data-pin-id"));
      });
      fetch(grid.getAttribute("data-reorder-url"), {
        method: "POST",
        body: fd,
        headers: { "HX-Request": "true" },
      });
    },
  });
})();
