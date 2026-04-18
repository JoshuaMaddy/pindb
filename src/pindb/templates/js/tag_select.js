// =============================================================================
// PinDB Tag Select — shared Tom Select helpers for tag/category selects
//
// Exposes window.TagSelect:
//   .TAG_CATEGORY_ICONS   — {category: lucide-icon-name}
//   .TAG_CATEGORY_COLORS  — {category: tailwind-class-string}
//   .tagOptionRender(item, escape) — dropdown option renderer
//   .tagItemRender(item, escape)   — selected item renderer
//   .tagSelectLucideCallbacks()    — Tom Select callbacks with MutationObserver
//                                    to re-run lucide after dynamic re-renders
// =============================================================================

(function () {
  "use strict";

  // Icons and color classes come from window.TagCategoryData (injected by base.py from tag_branding.py).
  // Handles two data shapes:
  //   - Static HTML options: Tom Select maps data-icon/data-color attrs → item.icon/item.color
  //   - API responses:       item.category is present, icon/color looked up from TagCategoryData
  function _resolveIconAndColor(item) {
    if (item.icon !== undefined || item.color !== undefined) {
      return { icon: item.icon || "tag", color: item.color || "" };
    }
    const cat = item.category || "general";
    const data = (window.TagCategoryData || {})[cat] || {};
    return {
      icon: data.icon || "tag",
      color: data.color || "",
    };
  }

  const TAG_CATEGORY_ICONS = Object.fromEntries(
    Object.entries(window.TagCategoryData || {}).map(([k, v]) => [k, v.icon])
  );
  const TAG_CATEGORY_COLORS = Object.fromEntries(
    Object.entries(window.TagCategoryData || {}).map(([k, v]) => [k, v.color])
  );

  function tagOptionRender(item, escape) {
    const { icon, color } = _resolveIconAndColor(item);
    return (
      `<div class="flex items-center gap-2">` +
      `<span class="inline-flex items-center p-0.5 rounded border ${color}">` +
      `<i data-lucide="${icon}" class="w-3.5 h-3.5 ${color}"></i>` +
      `</span>` +
      `<span>${escape(item.text)}</span>` +
      `</div>`
    );
  }

  function tagItemRender(item, escape) {
    const { icon, color } = _resolveIconAndColor(item);
    const catAttr = item.category
      ? ` data-category="${escape(item.category)}"`
      : "";
    return (
      `<div class="inline-flex items-center gap-1"${catAttr}>` +
      `<i data-lucide="${icon}" class="w-3 h-3 shrink-0 ${color}"></i>` +
      `<span>${escape(item.text)}</span>` +
      `</div>`
    );
  }

  // Returns a callbacks object to spread into Tom Select options.
  // Uses a MutationObserver on the dropdown to catch lazy option renders
  // (e.g. after the user types to filter), which would otherwise leave
  // freshly-inserted <i data-lucide> elements un-replaced.
  function tagSelectLucideCallbacks() {
    return {
      onDropdownOpen: function () {
        const dropdown = this.dropdown;
        if (!this._lucideObserver) {
          this._lucideObserver = new MutationObserver(function () {
            if (dropdown.querySelector("i[data-lucide]")) {
              lucide.createIcons({ nodes: [dropdown] });
            }
          });
          this._lucideObserver.observe(dropdown, {
            childList: true,
            subtree: true,
          });
        }
        lucide.createIcons({ nodes: [dropdown] });
      },
      onDropdownClose: function () {
        if (this._lucideObserver) {
          this._lucideObserver.disconnect();
          delete this._lucideObserver;
        }
      },
      onItemAdd: function () {
        const w = this.wrapper;
        requestAnimationFrame(function () {
          if (window.lucide) lucide.createIcons({ nodes: [w] });
        });
      },
      onInitialize: function () {
        if (window.lucide) lucide.createIcons();
      },
    };
  }

  // Syncs the selected category to data-selected-category on the wrapper so CSS
  // can color the entire single-select control box (not just the inner .item).
  function _syncSingleCategory(ts) {
    const val = ts.getValue();
    const item = ts.options[val];
    const cat = item && item.category;
    if (cat) {
      ts.wrapper.dataset.selectedCategory = cat;
    } else {
      delete ts.wrapper.dataset.selectedCategory;
    }
  }

  // Like tagSelectLucideCallbacks but also wires up category → wrapper sync
  // for single-select controls (Category field on tag form).
  function tagSingleSelectCallbacks() {
    const base = tagSelectLucideCallbacks();
    return Object.assign({}, base, {
      onInitialize: function () {
        _syncSingleCategory(this);
        if (window.lucide) lucide.createIcons();
      },
      onChange: function () {
        _syncSingleCategory(this);
      },
    });
  }

  window.TagSelect = {
    TAG_CATEGORY_ICONS,
    TAG_CATEGORY_COLORS,
    tagOptionRender,
    tagItemRender,
    tagSelectLucideCallbacks,
    tagSingleSelectCallbacks,
  };
})();
