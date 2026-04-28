(function () {
  var s = document.createElement("script");
  s.src = "https://cdn.jsdelivr.net/npm/sortablejs@1.15.6/Sortable.min.js";
  s.onload = function () {
    var grid = document.getElementById("pin-list");
    if (!grid) return;
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
  };
  document.head.appendChild(s);
})();
