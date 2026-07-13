// Island-side companion to templates/js/forms/form_persist.js.
//
// The legacy script owns SAVING (it serializes every named form field,
// including island-rendered inputs, into sessionStorage under
// `form_persist:<pathname>`) and restoring plain fields. Islands own
// restoring their OWN state from that same payload, because the legacy
// generic restore skips `[data-island]` subtrees.

const STORAGE_KEY = `form_persist:${location.pathname}`;

export function isReloadNavigation(): boolean {
  const entry = performance.getEntriesByType(
    "navigation",
  )[0] as PerformanceNavigationTiming | undefined;
  // "back_forward" is included alongside "reload": bfcache is supposed to make
  // this a non-issue for back/forward nav, but the legacy script's own
  // `beforeunload` listener disables bfcache in Firefox/Safari (and sometimes
  // Chrome), forcing a real reload that this restore path must also handle.
  return entry?.type === "reload" || entry?.type === "back_forward";
}

/** Persisted field payload, or null when absent/unparseable/not a reload. */
export function readPersistedFields(): Record<string, unknown> | null {
  if (!isReloadNavigation()) return null;
  const raw = sessionStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

/** Values for one repeated field name, e.g. grade_names -> ["Normal", ...]. */
export function persistedStringList(
  fields: Record<string, unknown> | null,
  name: string,
): string[] | null {
  const value = fields?.[name];
  if (!Array.isArray(value)) return null;
  if (!value.every((item) => typeof item === "string")) return null;
  return value;
}

// Form gates recompute on bubbling input/change; fire both after a
// programmatic restore so the submit state reflects restored values.
export function notifyFormOfRestore(el: HTMLElement): void {
  el.dispatchEvent(new Event("input", { bubbles: true }));
  el.dispatchEvent(new Event("change", { bubbles: true }));
}
