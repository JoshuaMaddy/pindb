(function () {
  var el = document.getElementById("pindb-tag-category-data");
  if (!el || !el.textContent) return;
  try {
    window.TagCategoryData = JSON.parse(el.textContent);
  } catch {}
})();
