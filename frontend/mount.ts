// Island loader. Scans for [data-island] mount points, dynamically imports
// /static/islands/<name>.js, and calls its default export
// (target, props) => unmount. Kept Svelte-free so this entry stays tiny;
// the Svelte runtime lands in a shared chunk loaded only when an island
// is actually present on the page.

type Unmount = () => void;

const mounted = new Map<HTMLElement, Unmount>();

// Reuse our own cache-buster for island imports (base.py renders this script
// tag with ?v=STATIC_CACHE_BUSTER).
const BUSTER = new URL(import.meta.url).searchParams.get("v") ?? "";

function readProps(el: HTMLElement): Record<string, unknown> {
  const s = el.querySelector(
    ':scope > script[type="application/json"][data-island-props]',
  );
  return s?.textContent ? JSON.parse(s.textContent) : {};
}

async function mountIsland(el: HTMLElement): Promise<void> {
  if (mounted.has(el)) return;
  // Reserve before the await so a rescan during import doesn't double-mount.
  mounted.set(el, () => {});
  const name = el.dataset.island;
  if (!name) return;
  const props = readProps(el);
  // htmx history restore re-serializes mounted DOM; drop stale rendered
  // children (keep the props <script>) so mount() starts from a clean target.
  el.querySelectorAll(":scope > *:not(script)").forEach((child) =>
    child.remove(),
  );
  try {
    const mod = await import(
      /* @vite-ignore */ `/static/islands/${name}.js?v=${BUSTER}`
    );
    if (!el.isConnected) {
      mounted.delete(el);
      return;
    }
    mounted.set(el, mod.default(el, props));
  } catch (err) {
    mounted.delete(el);
    console.error(`island "${name}" failed to mount`, err);
  }
}

function scan(root: ParentNode): void {
  root
    .querySelectorAll<HTMLElement>("[data-island]")
    .forEach((el) => void mountIsland(el));
}

scan(document);
// Whole-document rescan: outerHTML swaps detach evt.detail.target (same
// reasoning as formatLocalTimes in pindb_shell.js); idempotent via `mounted`.
document.addEventListener("htmx:afterSwap", () => scan(document));
document.addEventListener("htmx:oobAfterSwap", () => scan(document));
document.addEventListener("htmx:historyRestore", () => scan(document));
document.addEventListener("htmx:beforeCleanupElement", (evt) => {
  const el = evt.target;
  if (!(el instanceof HTMLElement)) return;
  const roots: HTMLElement[] = el.matches("[data-island]") ? [el] : [];
  el.querySelectorAll<HTMLElement>("[data-island]").forEach((n) =>
    roots.push(n),
  );
  for (const r of roots) {
    mounted.get(r)?.();
    mounted.delete(r);
  }
});
