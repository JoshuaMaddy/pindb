// =============================================================================
// PinDB shared WebP transcode helper
//
// Loaded (deferred, before its consumers) by the pin create/edit and bulk
// import pages. Exposes a single File -> WebP File primitive so each page no
// longer duplicates the encode/guard logic.
// =============================================================================

(function () {
  "use strict";

  var DEFAULT_QUALITY = 95;

  /**
   * Re-encode a raster image File to WebP when `globalThis.pindbWebpFromFile`
   * (the vendored encoder) is loaded. Returns the original file unchanged for
   * non-images, already-WebP files, a missing encoder, or any failure — so
   * callers can treat an unchanged return value as "left as-is".
   *
   * @param {File} file
   * @param {number} [quality]
   * @returns {Promise<File>}
   */
  globalThis.pindbTranscodeFileToWebp = async function (file, quality) {
    if (!file) return file;
    if (file.type === "image/webp") return file;
    if (file.type && file.type.indexOf("image/") !== 0) return file;
    var enc = globalThis.pindbWebpFromFile;
    if (typeof enc !== "function") return file;
    try {
      var blob = await enc(file, quality || DEFAULT_QUALITY);
      if (!blob || blob.size === 0) return file;
      var stem = file.name.replace(/\.[^.\\/]+$/, "") || "image";
      return new File([blob], stem + ".webp", {
        type: "image/webp",
        lastModified: Date.now(),
      });
    } catch {
      return file;
    }
  };
})();
