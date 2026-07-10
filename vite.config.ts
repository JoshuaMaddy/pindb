import { readdirSync } from "node:fs";

import { svelte } from "@sveltejs/vite-plugin-svelte";
import { defineConfig } from "vite";

// One entry per island: frontend/islands/<name>.entry.ts -> islands/<name>.js.
// Entry names are stable (no hash) because Python fetches them with
// ?v=STATIC_CACHE_BUSTER; shared code dedupes into content-hashed chunks/
// that only entry files reference, so Python never needs a manifest.
const islandEntries = Object.fromEntries(
  readdirSync("frontend/islands")
    .filter((f) => f.endsWith(".entry.ts"))
    .map((f) => [f.replace(".entry.ts", ""), `frontend/islands/${f}`]),
);

export default defineConfig({
  base: "/static/islands/",
  plugins: [svelte()],
  build: {
    outDir: "src/pindb/static/islands",
    emptyOutDir: true,
    target: "es2022",
    sourcemap: true,
    rollupOptions: {
      // App builds strip entry exports by default; islands are imported
      // dynamically by mount.js and must keep their default export.
      preserveEntrySignatures: "exports-only",
      input: { mount: "frontend/mount.ts", ...islandEntries },
      output: {
        entryFileNames: "[name].js",
        chunkFileNames: "chunks/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
      },
    },
  },
});
