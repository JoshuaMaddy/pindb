(function () {
  "use strict";

  // Configure marked to match server behavior:
  // headings render as plain paragraphs; images are stripped.
  if (typeof marked !== "undefined") {
    marked.use({
      renderer: {
        heading: function (token) {
          return "<p>" + token.text + "</p>\n";
        },
        image: function () {
          return "";
        },
      },
    });
  }

  function initMarkdownEditors() {
    document.querySelectorAll("[data-md-editor]").forEach(function (editorEl) {
      var fieldId = editorEl.getAttribute("data-md-editor");
      var hiddenInput = document.getElementById(fieldId);
      var previewEl = document.getElementById(fieldId + "-preview");

      if (!hiddenInput || typeof OverType === "undefined") return;

      var initialValue = hiddenInput.value || "";

      function updatePreview(markdown) {
        if (!previewEl || typeof marked === "undefined") return;
        previewEl.innerHTML = marked.parse(markdown);
      }

      new OverType(editorEl, {
        value: initialValue,
        theme: "cave",
        onChange: function (val) {
          hiddenInput.value = val;
          updatePreview(val);
        },
      });

      updatePreview(initialValue);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initMarkdownEditors);
  } else {
    initMarkdownEditors();
  }
})();
