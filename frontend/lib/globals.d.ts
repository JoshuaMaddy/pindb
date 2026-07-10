// Globals provided by vendored scripts loaded in base.py, for use inside
// islands. Extend as islands need more of the legacy surface.

declare global {
  // scripts/build-webp-encode.mjs -> static/vendor/pindb-webp/ (module script)
  function pindbWebpFromFile(
    file: File,
    quality: number,
  ): Promise<ArrayBuffer>;

  interface Window {
    /** Vendored tree-shaken lucide build (scripts/lucide/build-lucide.mjs). */
    lucide?: {
      createIcons(options?: { nodes?: Element[] }): void;
    };
    htmx?: {
      process(el: Element): void;
      ajax(
        method: string,
        url: string,
        options?: {
          target?: string;
          swap?: string;
          values?: Record<string, unknown>;
        },
      ): void;
    };
    /** Category branding map injected by base.py (tags/tag_category_bootstrap.js). */
    TagCategoryData?: Record<string, { icon?: string; color?: string }>;
  }
}

export {};
