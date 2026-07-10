// Typed wrapper over the vendored client-side WebP pipeline.
//
// shared/webp_transcode.js (classic script, loaded per-page) exposes
// pindbTranscodeFileToWebp(file, quality) -> Promise<File>, returning the
// original file unchanged when the encoder is missing or the file is not a
// transcodable raster image. The WASM encoder itself stays vendored
// (static/vendor/pindb-webp/) — it is NOT bundled into islands.

export const PIN_IMAGE_WEBP_QUALITY = 95;

declare global {
  function pindbTranscodeFileToWebp(
    file: File,
    quality: number,
  ): Promise<File>;
}

export async function transcodeToWebp(
  file: File,
  quality: number = PIN_IMAGE_WEBP_QUALITY,
): Promise<File> {
  if (typeof globalThis.pindbTranscodeFileToWebp !== "function") return file;
  return globalThis.pindbTranscodeFileToWebp(file, quality);
}

/** Replace a file input's file list with the given file. */
export function setInputFile(input: HTMLInputElement, file: File): void {
  const transfer = new DataTransfer();
  transfer.items.add(file);
  input.files = transfer.files;
}
