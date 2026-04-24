#!/usr/bin/env node
// Copy pinned JS/CSS vendor assets from node_modules into src/pindb/static/vendor/.
// Lucide is *not* copied: run `node scripts/lucide/build-lucide.mjs` (see `npm run build`).
// Output directory is gitignored.

import { cp, mkdir, rm, access } from "node:fs/promises";
import { dirname, resolve } from "node:path";

const ROOT = resolve(
  new URL("..", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1"),
);
const VENDOR = resolve(ROOT, "src/pindb/static/vendor");

const FILES = [
  ["htmx.org/dist/htmx.min.js", "htmx.min.js"],
  ["notyf/notyf.min.js", "notyf.min.js"],
  ["notyf/notyf.min.css", "notyf.min.css"],
  [
    "tom-select/dist/js/tom-select.complete.min.js",
    "tom-select.complete.min.js",
  ],
  [
    "tom-select/dist/css/tom-select.default.min.css",
    "tom-select.default.min.css",
  ],
  ["alpinejs/dist/cdn.min.js", "alpine.min.js"],
  ["overtype/dist/overtype.min.js", "overtype.min.js"],
  ["marked/lib/marked.umd.js", "marked.min.js"],
];

async function exists(p) {
  try {
    await access(p);
    return true;
  } catch {
    return false;
  }
}

await rm(VENDOR, { recursive: true, force: true });
await mkdir(VENDOR, { recursive: true });

let failed = 0;
for (const [rel, out] of FILES) {
  const src = resolve(ROOT, "node_modules", rel);
  const dst = resolve(VENDOR, out);
  if (!(await exists(src))) {
    console.error(`vendor: MISSING ${src}`);
    failed += 1;
    continue;
  }
  await mkdir(dirname(dst), { recursive: true });
  await cp(src, dst);
  console.log(`vendor: ${rel} -> static/vendor/${out}`);
}

if (failed > 0) {
  console.error(`vendor: ${failed} file(s) missing. Run 'npm ci' first.`);
  process.exit(1);
}
