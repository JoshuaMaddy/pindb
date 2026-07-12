<script lang="ts" module>
  export type Option = {
    value: string;
    text: string;
    category?: string;
    icon?: string;
    color?: string;
    thumbnail?: string;
  };

  // Per-instance suffix for listbox/option ids: bulk grids mount one widget
  // per row with no id/name, and duplicate DOM ids break aria-activedescendant
  // (and any id-based lookup) on every row but the first.
  let instances = 0;
</script>

<script lang="ts">
  import type { Component } from "svelte";
  import { tick, untrack } from "svelte";

  import BookUser from "@lucide/svelte/icons/book-user";
  import Building2 from "@lucide/svelte/icons/building-2";
  import ChevronDown from "@lucide/svelte/icons/chevron-down";
  import Copyright from "@lucide/svelte/icons/copyright";
  import Gem from "@lucide/svelte/icons/gem";
  import Info from "@lucide/svelte/icons/info";
  import PaintBucket from "@lucide/svelte/icons/paint-bucket";
  import PawPrint from "@lucide/svelte/icons/paw-print";
  import Tag from "@lucide/svelte/icons/tag";
  import User from "@lucide/svelte/icons/user";
  import X from "@lucide/svelte/icons/x";

  // Native replacement for the Tom Select wrapper: chips + dropdown built
  // from plain Svelte state. A synced (visually hidden) <select> stays in the
  // DOM so form submission, HTMX `change` triggers, form gates and e2e value
  // assertions all read standard elements. Test hooks mirror the legacy
  // contract: [data-multiselect] root, [data-ms-control], [data-ms-dropdown],
  // [data-selectable] options (create option adds [data-ms-create]) and
  // [data-value] chips.

  // Tag category icons are a fixed server-side set (tag_branding.py); a
  // static map keeps @lucide/svelte imports tree-shakeable.
  const ICONS: Record<string, Component> = {
    tag: Tag,
    copyright: Copyright,
    user: User,
    "book-user": BookUser,
    "paw-print": PawPrint,
    "building-2": Building2,
    info: Info,
    gem: Gem,
    "paint-bucket": PaintBucket,
  };

  type CategoryData = Record<string, { icon?: string; color?: string }>;

  let {
    value = $bindable([]),
    options = [],
    multiple = true,
    placeholder = "",
    create = false,
    loadUrl = "",
    loadFn,
    name = "",
    id = "",
    tagMode = false,
    tagSingleMode = false,
    adoptedSelect = null,
    class: className = "",
    onValueChange,
    onOptionCreate,
  }: {
    value?: string[];
    options?: Option[];
    multiple?: boolean;
    placeholder?: string;
    create?: boolean;
    loadUrl?: string;
    /** Custom remote loader; takes precedence over loadUrl. */
    loadFn?: (query: string) => Promise<Option[]>;
    name?: string;
    id?: string;
    /** Category chip rendering (icon + per-category colors). */
    tagMode?: boolean;
    /** Single-select variant: chip renderers + control-box category color. */
    tagSingleMode?: boolean;
    /**
     * Enhance an existing server-rendered select (moved inside this
     * component, kept in sync, real change events dispatched on it) instead
     * of rendering an internal one — preserves form submission, HTMX
     * triggers and form-gate reads on the original element.
     */
    adoptedSelect?: HTMLSelectElement | null;
    class?: string;
    onValueChange?: (values: string[], selected: Option[]) => void;
    onOptionCreate?: (option: Option) => void;
  } = $props();

  let rootEl: HTMLElement;
  let controlEl: HTMLElement;
  let dropEl: HTMLElement | undefined = $state();
  let inputEl: HTMLInputElement | undefined = $state();
  let selectEl: HTMLSelectElement | undefined = $state();

  let items = $state<Option[]>([]);
  let loaded = $state<Option[]>([]);
  let query = $state("");
  let open = $state(false);
  let active = $state(0);
  let loading = $state(false);

  const isSingle = $derived(!multiple || tagSingleMode);
  const hasRemote = $derived(Boolean(loadFn) || Boolean(loadUrl));

  const uid = ++instances;
  // id/name are static per mount (islands remount on swap).
  // svelte-ignore state_referenced_locally
  const listboxId = `${id || name || `multiselect-${uid}`}-listbox`;
  const optionId = (index: number) => `${listboxId}-opt-${index}`;

  function categoryData(): CategoryData {
    return (
      (window as { TagCategoryData?: CategoryData }).TagCategoryData ?? {}
    );
  }

  // Mirrors the legacy renderer's resolution: explicit icon/color on the
  // option wins; otherwise look the category up in the injected branding map.
  function brand(option: Option): { icon: Component; color: string } {
    if (option.icon !== undefined || option.color !== undefined) {
      return {
        icon: ICONS[option.icon ?? "tag"] ?? Tag,
        color: option.color ?? "",
      };
    }
    const data = categoryData()[option.category ?? "general"] ?? {};
    return { icon: ICONS[data.icon ?? "tag"] ?? Tag, color: data.color ?? "" };
  }

  function findKnown(optionValue: string): Option | undefined {
    return (
      options.find((option) => option.value === optionValue) ??
      loaded.find((option) => option.value === optionValue) ??
      untrack(() => items).find((option) => option.value === optionValue)
    );
  }

  // Initial selection: resolve the value prop against the managed options.
  {
    const initial = untrack(() => [...value]);
    items = initial.map(
      (entry) => findKnown(entry) ?? { value: entry, text: entry },
    );
  }

  const pool = $derived.by(() => {
    const seen = new Set<string>();
    const merged: Option[] = [];
    for (const option of [...options, ...loaded]) {
      if (seen.has(option.value)) continue;
      seen.add(option.value);
      merged.push(option);
    }
    return merged;
  });

  const filtered = $derived.by(() => {
    const tokens = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
    const taken = new Set(items.map((item) => item.value));
    return pool
      .filter((option) => {
        if (multiple && taken.has(option.value)) return false;
        if (!tokens.length) return true;
        const text = option.text.toLowerCase();
        return tokens.every((token) => text.includes(token));
      })
      .slice(0, 50);
  });

  const showCreate = $derived.by(() => {
    const trimmed = query.trim();
    if (!create || !trimmed) return false;
    const lower = trimmed.toLowerCase();
    const clash = (option: Option) =>
      option.value.toLowerCase() === lower ||
      option.text.toLowerCase() === lower;
    return !pool.some(clash) && !items.some(clash);
  });

  const optionCount = $derived(filtered.length + (showCreate ? 1 : 0));

  // Adopted selects keep their full server-rendered option list (it doubles
  // as the local option pool); selection state and any widget-discovered
  // entries are written back so the form submits the real element.
  function syncAdopted(): void {
    const adopted = adoptedSelect;
    if (!adopted) return;
    const wanted = new Set(items.map((item) => item.value));
    const present = new Set<string>();
    for (const option of Array.from(adopted.options)) {
      option.selected = wanted.has(option.value);
      present.add(option.value);
    }
    for (const item of items) {
      if (present.has(item.value)) continue;
      adopted.appendChild(new Option(item.text, item.value, false, true));
    }
    if (!adopted.multiple && items.length === 0) adopted.selectedIndex = -1;
  }

  function pushValue(): void {
    value = items.map((item) => item.value);
    syncAdopted();
    onValueChange?.([...value], [...items]);
    void tick().then(() => {
      (adoptedSelect ?? selectEl)?.dispatchEvent(
        new Event("change", { bubbles: true }),
      );
    });
  }

  // Closing always drops the query: a stale one keeps the filter live and,
  // in single mode, hides the selected chip behind the text the user typed.
  function close(): void {
    open = false;
    query = "";
    active = 0;
  }

  function selectOption(option: Option): void {
    if (items.some((item) => item.value === option.value)) {
      // Keyed {#each} — a duplicate value is a hard render error, not a
      // cosmetic double chip.
      if (!multiple) close();
      return;
    }
    items = multiple ? [...items, option] : [option];
    query = "";
    active = 0;
    if (!multiple) open = false;
    pushValue();
    inputEl?.focus();
  }

  function createFromQuery(): void {
    const trimmed = query.trim();
    if (!trimmed) return;
    const option: Option = { value: trimmed, text: trimmed };
    onOptionCreate?.(option);
    selectOption(option);
  }

  function removeItem(optionValue: string): void {
    items = items.filter((item) => item.value !== optionValue);
    pushValue();
  }

  function pickActive(): void {
    if (active < filtered.length) {
      const option = filtered[active];
      if (option) selectOption(option);
    } else if (showCreate) {
      createFromQuery();
    }
  }

  function onControlClick(): void {
    open = true;
    inputEl?.focus();
  }

  // The chevron is the one part of the control that toggles: clicking the
  // text area of an open widget means "put the caret here", not "close".
  function onChevronClick(event: MouseEvent): void {
    event.stopPropagation();
    if (open) {
      // No refocus here — its mousedown is prevented, so the input never lost
      // focus, and calling focus() again would fire onfocus and reopen.
      close();
      return;
    }
    open = true;
    inputEl?.focus();
  }

  // Buttons inside the control take focus on mousedown, which would blur the
  // input (and, for the chip "×", leave focus on a node that's about to be
  // removed). Keep focus on the input; the click still fires.
  function keepFocus(event: MouseEvent): void {
    event.preventDefault();
  }

  function onKeydown(event: KeyboardEvent): void {
    if (event.key === "Escape") {
      if (!open) return;
      // Don't let a dropdown-closing Escape also close the modal around it.
      event.stopPropagation();
      close();
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      if (!open) open = true;
      else active = Math.min(active + 1, Math.max(optionCount - 1, 0));
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      if (!open) open = true;
      else active = Math.max(active - 1, 0);
      return;
    }
    if (open && (event.key === "Home" || event.key === "End")) {
      event.preventDefault();
      active = event.key === "Home" ? 0 : Math.max(optionCount - 1, 0);
      return;
    }
    if (event.key === "Enter") {
      if (!open) return;
      event.preventDefault();
      pickActive();
      return;
    }
    if (event.key === "Backspace" && !query && items.length > 0) {
      // Single mode has no chip "×" — backspace is the only way to clear it.
      removeItem(items[items.length - 1].value);
    }
  }

  // Tab (or any focus move out of the widget) closes. Clicks inside the
  // dropdown never reach here: its mousedown is prevented, so the input
  // keeps focus and the click lands on a live option.
  function onFocusOut(event: FocusEvent): void {
    if (!open) return;
    const next = event.relatedTarget as Node | null;
    if (next && (rootEl.contains(next) || dropEl?.contains(next))) return;
    close();
  }

  // Adopt: pull the server-rendered select inside this component (so the
  // generic form-persist restore skips it via [data-island]) and hide it —
  // it stays the form-submitting element.
  $effect(() => {
    const adopted = adoptedSelect;
    if (!adopted) return;
    untrack(() => {
      rootEl.insertBefore(adopted, rootEl.firstChild);
      adopted.classList.add("sr-only");
      adopted.tabIndex = -1;
      adopted.setAttribute("aria-hidden", "true");
      // The client-side gate owns requiredness; a hidden required select
      // would trap native constraint-validation focus.
      adopted.removeAttribute("required");
      syncAdopted();
    });
  });

  // Remote load: debounced on keystrokes while open, merged into the pool.
  let loadTimer: ReturnType<typeof setTimeout> | undefined;
  let loadSeq = 0;
  $effect(() => {
    const trimmed = query.trim();
    if (!open || !trimmed || !hasRemote) return;
    clearTimeout(loadTimer);
    const seq = ++loadSeq;
    loadTimer = setTimeout(async () => {
      let results: Option[] = [];
      loading = true;
      try {
        if (loadFn) {
          results = await loadFn(trimmed);
        } else {
          const separator = loadUrl.includes("?") ? "&" : "?";
          const response = await fetch(
            `${loadUrl}${separator}q=${encodeURIComponent(trimmed)}`,
          );
          results = response.ok ? await response.json() : [];
        }
      } catch {
        results = [];
      }
      if (seq !== loadSeq) return;
      loading = false;
      const known = new Set(
        untrack(() => loaded).map((option) => option.value),
      );
      const fresh = (results ?? []).filter(
        (option) => !known.has(option.value),
      );
      if (fresh.length) loaded = [...loaded, ...fresh];
    }, 250);
    return () => {
      clearTimeout(loadTimer);
      loading = false;
    };
  });

  // External value writes (paste-column, draft restore) rebuild the items.
  // De-duplicated: values arrive from clipboard/draft JSON, and the keyed
  // {#each} over items throws on a repeated key.
  $effect(() => {
    const snapshot = [...new Set(value)];
    untrack(() => {
      const current = items.map((item) => item.value);
      if (JSON.stringify(snapshot) === JSON.stringify(current)) return;
      items = snapshot.map(
        (entry) => findKnown(entry) ?? { value: entry, text: entry },
      );
    });
  });

  // Managed-option changes flow into the selection: renamed options update
  // their chip, options that left the prop (e.g. a sibling row's name was
  // cleared) drop their selection. Options discovered via remote load or
  // create are never in the prop map and are left alone.
  let prevManaged = new Map<string, Option>();
  $effect(() => {
    const next = new Map(options.map((option) => [option.value, option]));
    untrack(() => {
      let mutated = false;
      const kept = items
        .filter((item) => {
          if (prevManaged.has(item.value) && !next.has(item.value)) {
            mutated = true;
            return false;
          }
          return true;
        })
        .map((item) => {
          const managed = next.get(item.value);
          if (
            managed &&
            (managed.text !== item.text || managed.category !== item.category)
          ) {
            mutated = true;
            return { ...item, ...managed };
          }
          return item;
        });
      if (mutated) {
        items = kept;
        pushValue();
      }
      prevManaged = next;
    });
  });

  // Fixed positioning escapes overflow-clipped containers (bulk tables) the
  // way dropdownParent="body" did for Tom Select.
  const GAP = 2;
  const EDGE = 8;
  const MAX_DROP_HEIGHT = 256; // matches the max-h-64 class

  // The style is written straight to the element, not through state: the two
  // passes below must measure the layout the first pass produced, and a
  // state-bound style attribute only lands after the effect flush.
  function applyDropStyle(
    left: number,
    anchor: string,
    minWidth: number,
    maxHeight: number,
  ): void {
    if (!dropEl) return;
    dropEl.style.cssText =
      `position:fixed;left:${left}px;${anchor};` +
      `min-width:${minWidth}px;max-width:24rem;max-height:${maxHeight}px;`;
  }

  function positionDropdown(): void {
    if (!controlEl || !dropEl) return;
    const rect = controlEl.getBoundingClientRect();
    const natural = Math.min(dropEl.scrollHeight, MAX_DROP_HEIGHT);
    const below = window.innerHeight - rect.bottom - GAP - EDGE;
    const above = rect.top - GAP - EDGE;
    // Flip above the control only when the list genuinely doesn't fit below
    // and there is more room up there.
    const flip = natural > below && above > below;
    const maxHeight = Math.max(
      96,
      Math.min(MAX_DROP_HEIGHT, flip ? above : below),
    );
    const width = dropEl.offsetWidth || rect.width;
    const left = Math.max(
      EDGE,
      Math.min(rect.left, window.innerWidth - width - EDGE),
    );
    // `wantTop` is the dropdown's top edge below the control, its bottom edge
    // when flipped.
    const anchorFor = (edge: number) =>
      flip ? `bottom:${window.innerHeight - edge}px` : `top:${edge}px`;
    const wantTop = flip ? rect.top - GAP : rect.bottom + GAP;
    applyDropStyle(left, anchorFor(wantTop), rect.width, maxHeight);

    // A transformed/filtered/contained ancestor (modal, card, animated
    // container) becomes the containing block for position:fixed, so those
    // viewport coordinates land offset and the dropdown drifts over the
    // control. Measure where it actually ended up and correct by the delta.
    const actual = dropEl.getBoundingClientRect();
    const dx = left - actual.left;
    const dy = flip
      ? wantTop - actual.bottom
      : wantTop - actual.top;
    if (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5) return;
    applyDropStyle(left + dx, anchorFor(wantTop + dy), rect.width, maxHeight);
  }

  // Re-anchor whenever the list or the control changes size: adding a chip
  // wraps the control onto a second line, and a dropdown pinned to the old
  // rect then sits on top of it.
  $effect(() => {
    if (!open) return;
    void optionCount;
    void items.length;
    positionDropdown();
  });

  $effect(() => {
    if (!open) return;
    const reposition = () => positionDropdown();
    const onDocPointer = (event: PointerEvent) => {
      const target = event.target as Node;
      if (rootEl.contains(target) || dropEl?.contains(target)) return;
      close();
    };
    const observer = new ResizeObserver(reposition);
    observer.observe(controlEl);
    if (dropEl) observer.observe(dropEl);
    window.addEventListener("scroll", reposition, true);
    window.addEventListener("resize", reposition);
    document.addEventListener("pointerdown", onDocPointer, true);
    return () => {
      observer.disconnect();
      window.removeEventListener("scroll", reposition, true);
      window.removeEventListener("resize", reposition);
      document.removeEventListener("pointerdown", onDocPointer, true);
    };
  });

  // Keep the highlight inside the list as it shrinks under the query, and
  // scroll it into view so arrow-key nav doesn't run off the visible area.
  $effect(() => {
    const count = optionCount;
    void query;
    untrack(() => {
      const clamped = Math.min(active, Math.max(count - 1, 0));
      if (clamped !== active) active = clamped;
    });
  });

  $effect(() => {
    if (!open) return;
    const index = active;
    dropEl
      ?.querySelector(`[data-index="${index}"]`)
      ?.scrollIntoView({ block: "nearest" });
  });

  const singleBrandColor = $derived(
    tagSingleMode && items[0] ? brand(items[0]).color : "",
  );

  const controlClass = $derived(
    "flex w-full items-center gap-1 rounded-lg border px-2 " +
      // Single mode never wraps (the chevron stays on the item's line);
      // multi mode wraps chips onto new lines as they accumulate.
      (isSingle ? "flex-nowrap py-2 " : "flex-wrap py-1 min-h-9 ") +
      (singleBrandColor || "border-lightest bg-lighter text-base-text") +
      " cursor-text",
  );

  const chipClass = "inline-flex items-center gap-1 rounded-lg border px-1.5";
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  data-multiselect
  bind:this={rootEl}
  class="relative min-w-0 {className}"
  data-selected-category={tagSingleMode ? items[0]?.category : undefined}
  onfocusout={onFocusOut}
>
  {#if !adoptedSelect}
    <select
      bind:this={selectEl}
      {multiple}
      name={name || undefined}
      id={id || undefined}
      tabindex="-1"
      aria-hidden="true"
      class="sr-only"
    >
      {#each items as item (item.value)}
        <option value={item.value} selected>{item.text}</option>
      {/each}
    </select>
  {/if}

  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div data-ms-control bind:this={controlEl} class={controlClass} onclick={onControlClick}>
    {#each multiple ? items : query ? [] : items as item (item.value)}
      {@const itemBrand = brand(item)}
      <div
        data-value={item.value}
        data-category={tagMode || tagSingleMode ? item.category : undefined}
        class="{chipClass} {multiple
          ? (tagMode && item.category
              ? brand(item).color
              : 'bg-lighter border-lightest text-base-text') + ' pr-0'
          : 'border-0 bg-transparent px-0'}"
      >
        {#if tagMode || tagSingleMode}
          {@const Icon = itemBrand.icon}
          <!-- Color classes ride the svg directly (its own utility beats the
               base layer's universal color rule), mirroring the legacy
               renderer. -->
          <Icon class="h-3 w-3 shrink-0 {itemBrand.color}" />
        {:else if item.thumbnail}
          <img
            src={item.thumbnail}
            class="h-6 w-6 shrink-0 rounded bg-main object-contain"
            alt=""
          />
        {/if}
        <span>{item.text}</span>
        {#if multiple}
          <button
            type="button"
            class="ml-0.5 inline-flex cursor-pointer appearance-none items-center rounded-none border-0 border-l border-current bg-transparent px-1.5 text-current"
            aria-label="Remove {item.text}"
            onmousedown={keepFocus}
            onclick={(event) => {
              event.stopPropagation();
              removeItem(item.value);
              // Keyboard activation (detail 0) leaves focus on a button that
              // is about to be removed — put it back on the input. A mouse
              // click must not, or every chip removal would open the list.
              if (event.detail === 0) inputEl?.focus();
            }}
          >
            <X class="h-3 w-3" />
          </button>
        {/if}
      </div>
    {/each}
    <input
      bind:this={inputEl}
      type="text"
      autocomplete="off"
      role="combobox"
      aria-expanded={open}
      aria-haspopup="listbox"
      aria-autocomplete="list"
      aria-controls={listboxId}
      aria-activedescendant={open && optionCount > 0
        ? optionId(active)
        : undefined}
      class="flex-1 border-0 bg-transparent p-0 text-base-text outline-none {isSingle
        ? 'w-0 min-w-0'
        : 'min-w-8'}"
      placeholder={items.length === 0 ? placeholder : ""}
      bind:value={query}
      oninput={() => (open = true)}
      onkeydown={onKeydown}
    />
    {#if isSingle}
      <button
        type="button"
        tabindex="-1"
        aria-label={open ? "Close options" : "Show options"}
        class="inline-flex shrink-0 cursor-pointer appearance-none items-center border-0 bg-transparent p-0 text-current"
        onmousedown={keepFocus}
        onclick={onChevronClick}
      >
        <ChevronDown
          class="h-4 w-4 shrink-0 opacity-70 transition-transform {open
            ? 'rotate-180'
            : ''}"
        />
      </button>
    {/if}
  </div>

  {#if open}
    <!-- position:fixed escapes overflow-clipped table containers; the high
         z-index needs no body portal (a portal would detach the subtree from
         Svelte's root-scoped event delegation and dead-click every option).
         Its style is written imperatively by positionDropdown(), which needs
         to measure the layout it produced — see the two-pass note there.
         Each option prevents its own mousedown (not the container's, which
         would also swallow scrollbar drags) so clicking one never blurs the
         input — a blur closes the list out from under the click. -->
    <div
      data-ms-dropdown
      bind:this={dropEl}
      id={listboxId}
      role="listbox"
      aria-multiselectable={multiple}
      tabindex="-1"
      class="z-[100] max-h-64 overflow-y-auto rounded-lg border border-lightest bg-lighter shadow-lg"
    >
      {#each filtered as option, index (option.value)}
        {@const optionBrand = brand(option)}
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <div
          data-selectable
          data-value={option.value}
          data-index={index}
          id={optionId(index)}
          role="option"
          aria-selected={items.some((item) => item.value === option.value)}
          tabindex="-1"
          class="cursor-pointer px-2 py-1.5 text-base-text {index === active
            ? 'bg-lighter-hover'
            : 'bg-lighter'}"
          onmouseenter={() => (active = index)}
          onmousedown={keepFocus}
          onclick={() => selectOption(option)}
        >
          {#if tagMode || tagSingleMode}
            {@const Icon = optionBrand.icon}
            <div class="flex items-center gap-2">
              <span
                class="inline-flex items-center rounded border p-0.5 {optionBrand.color}"
              >
                <Icon class="h-3.5 w-3.5 {optionBrand.color}" />
              </span>
              <span>{option.text}</span>
            </div>
          {:else if option.thumbnail}
            <div class="flex items-center gap-1">
              <img
                src={option.thumbnail}
                class="mr-2 h-6 w-6 shrink-0 rounded bg-main object-contain"
                alt=""
              />
              <span>{option.text}</span>
            </div>
          {:else}
            {option.text}
          {/if}
        </div>
      {/each}
      {#if showCreate}
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <div
          data-selectable
          data-ms-create
          data-index={filtered.length}
          id={optionId(filtered.length)}
          role="option"
          aria-selected="false"
          tabindex="-1"
          class="cursor-pointer px-2 py-1.5 text-base-text {active ===
          filtered.length
            ? 'bg-lighter-hover'
            : 'bg-lighter'}"
          onmouseenter={() => (active = filtered.length)}
          onmousedown={keepFocus}
          onclick={createFromQuery}
        >
          Add <span class="font-semibold">{query.trim()}</span>…
        </div>
      {/if}
      {#if optionCount === 0}
        <div class="no-results px-2 py-1.5 text-lightest-hover">
          {#if loading}
            Searching…
          {:else if query.trim()}
            No results found
          {:else if hasRemote}
            Start typing to search…
          {:else}
            No options
          {/if}
        </div>
      {/if}
    </div>
  {/if}
</div>
