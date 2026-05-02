/**
 * Rolldown entry: bundles @jsquash/webp encode + wasm into static/vendor.
 */
import encode from "@jsquash/webp/encode";

/**
 * @param {File} file
 * @param {number} quality 0–100 (libwebp)
 * @returns {Promise<Blob>}
 */
async function fileToWebpBlob(file, quality) {
  const bitmap = await createImageBitmap(file);
  try {
    const w = bitmap.width;
    const h = bitmap.height;
    let imageData;
    if (typeof OffscreenCanvas !== "undefined") {
      const canvas = new OffscreenCanvas(w, h);
      const ctx = canvas.getContext("2d", { willReadFrequently: true });
      if (!ctx) throw new Error("no 2d context");
      ctx.drawImage(bitmap, 0, 0);
      imageData = ctx.getImageData(0, 0, w, h);
    } else {
      const canvas = document.createElement("canvas");
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext("2d", { willReadFrequently: true });
      if (!ctx) throw new Error("no 2d context");
      ctx.drawImage(bitmap, 0, 0);
      imageData = ctx.getImageData(0, 0, w, h);
    }
    const buffer = await encode(imageData, { quality });
    return new Blob([buffer], { type: "image/webp" });
  } finally {
    bitmap.close();
  }
}

globalThis.pindbWebpFromFile = fileToWebpBlob;
