#!/usr/bin/env node
/**
 * Bundle @jsquash/webp (ESM) into static/vendor/pindb-webp/ and copy libwebp
 * .wasm binaries next to Rolldown chunks so import.meta.url resolves.
 */
import { cp, mkdir, rm } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "rolldown";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const OUT_DIR = resolve(ROOT, "src/pindb/static/vendor/pindb-webp");
const CODEC_ENC = resolve(ROOT, "node_modules/@jsquash/webp/codec/enc");
const WASM_FILES = ["webp_enc.wasm", "webp_enc_simd.wasm"];

await rm(OUT_DIR, { recursive: true, force: true });
await mkdir(OUT_DIR, { recursive: true });

await build({
  input: resolve(ROOT, "scripts/_pindb_webp_entry.mjs"),
  output: {
    dir: OUT_DIR,
    format: "esm",
    entryFileNames: "pindb-webp-encode.js",
    chunkFileNames: "[name]-[hash].js",
  },
});

for (const name of WASM_FILES) {
  await cp(resolve(CODEC_ENC, name), resolve(OUT_DIR, name));
}

console.log("webp-encode: built", OUT_DIR);
