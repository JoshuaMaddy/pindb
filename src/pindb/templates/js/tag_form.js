document.addEventListener("DOMContentLoaded", function () {
  var _tagRender = {
    option: TagSelect.tagOptionRender,
    item: TagSelect.tagItemRender,
  };
  var _noResults = {
    no_results: function (data) {
      var msg =
        data.input && data.input.length > 0
          ? "No results found"
          : "Start typing to search\u2026";
      return '<div class="no-results">' + msg + "</div>";
    },
  };

  document.querySelectorAll("select.multi-select").forEach(function (el) {
    var optionsUrl = el.dataset.optionsUrl;
    new TomSelect(
      el,
      Object.assign(
        {
          load: function (query, callback) {
            var sep = optionsUrl.includes("?") ? "&" : "?";
            fetch(optionsUrl + sep + "q=" + encodeURIComponent(query))
              .then(function (r) {
                return r.json();
              })
              .then(callback)
              .catch(function () {
                callback();
              });
          },
          shouldLoad: function (q) {
            return q.length > 0;
          },
          maxItems: null,
          valueField: "value",
          labelField: "text",
          persist: true,
          plugins: ["caret_position", "remove_button"],
          render: Object.assign({}, _noResults, _tagRender),
        },
        TagSelect.tagSelectLucideCallbacks(),
      ),
    );
  });

  document.querySelectorAll("select.single-select").forEach(function (el) {
    new TomSelect(
      el,
      Object.assign(
        {
          render: _tagRender,
        },
        TagSelect.tagSingleSelectCallbacks(),
      ),
    );
  });

  document.querySelectorAll("select.alias-select").forEach(function (el) {
    new TomSelect(el, {
      maxItems: null,
      create: true,
      persist: false,
      plugins: ["remove_button"],
      onInitialize: function () {
        this.addItems([]);
      },
    });
  });
});
