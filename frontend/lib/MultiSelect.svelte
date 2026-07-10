<script lang="ts" module>
  export type Option = {
    value: string;
    text: string;
    category?: string;
    icon?: string;
    color?: string;
    thumbnail?: string;
  };
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
  let dropStyle = $state("");

  const isSingle = $derived(!multiple || tagSingleMode);
  const hasRemote = $derived(Boolean(loadFn) || Boolean(loadUrl));

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

  function selectOption(option: Option): void {
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

  function onKeydown(event: KeyboardEvent): void {
    if (event.key === "Escape") {
      open = false;
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
      active = Math.max(active - 1, 0);
      return;
    }
    if (event.key === "Enter") {
      if (!open) return;
      event.preventDefault();
      pickActive();
      return;
    }
    if (
      event.key === "Backspace" &&
      multiple &&
      !query &&
      items.length > 0
    ) {
      removeItem(items[items.length - 1].value);
    }
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
      const known = new Set(
        untrack(() => loaded).map((option) => option.value),
      );
      const fresh = (results ?? []).filter(
        (option) => !known.has(option.value),
      );
      if (fresh.length) loaded = [...loaded, ...fresh];
    }, 250);
    return () => clearTimeout(loadTimer);
  });

  // External value writes (paste-column, draft restore) rebuild the items.
  $effect(() => {
    const snapshot = [...value];
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
  function positionDropdown(): void {
    if (!controlEl) return;
    const rect = controlEl.getBoundingClientRect();
    dropStyle =
      `position:fixed;left:${rect.left}px;top:${rect.bottom + 2}px;` +
      `min-width:${rect.width}px;max-width:24rem;`;
  }

  $effect(() => {
    if (!open) return;
    active = 0;
    positionDropdown();
    const reposition = () => positionDropdown();
    const onDocPointer = (event: PointerEvent) => {
      const target = event.target as Node;
      if (rootEl.contains(target) || dropEl?.contains(target)) return;
      open = false;
    };
    window.addEventListener("scroll", reposition, true);
    window.addEventListener("resize", reposition);
    document.addEventListener("pointerdown", onDocPointer, true);
    return () => {
      window.removeEventListener("scroll", reposition, true);
      window.removeEventListener("resize", reposition);
      document.removeEventListener("pointerdown", onDocPointer, true);
    };
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

<div
  data-multiselect
  bind:this={rootEl}
  class="relative min-w-0 {className}"
  data-selected-category={tagSingleMode ? items[0]?.category : undefined}
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
            onclick={(event) => {
              event.stopPropagation();
              removeItem(item.value);
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
      aria-controls="{id || name || 'multiselect'}-listbox"
      class="flex-1 border-0 bg-transparent p-0 text-base-text outline-none {isSingle
        ? 'w-0 min-w-0'
        : 'min-w-8'}"
      placeholder={items.length === 0 ? placeholder : ""}
      bind:value={query}
      onfocus={() => (open = true)}
      onkeydown={onKeydown}
    />
    {#if isSingle}
      <ChevronDown class="h-4 w-4 shrink-0 opacity-70" />
    {/if}
  </div>

  {#if open}
    <!-- position:fixed escapes overflow-clipped table containers; the high
         z-index needs no body portal (a portal would detach the subtree from
         Svelte's root-scoped event delegation and dead-click every option). -->
    <div
      data-ms-dropdown
      bind:this={dropEl}
      id="{id || name || 'multiselect'}-listbox"
      role="listbox"
      class="z-[100] max-h-64 overflow-y-auto rounded-lg border border-lightest bg-lighter shadow-lg"
      style={dropStyle}
    >
      {#each filtered as option, index (option.value)}
        {@const optionBrand = brand(option)}
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <div
          data-selectable
          data-value={option.value}
          role="option"
          aria-selected={index === active}
          tabindex="-1"
          class="cursor-pointer px-2 py-1.5 text-base-text {index === active
            ? 'bg-lighter-hover'
            : 'bg-lighter'}"
          onmouseenter={() => (active = index)}
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
          role="option"
          aria-selected={active === filtered.length}
          tabindex="-1"
          class="cursor-pointer px-2 py-1.5 text-base-text {active ===
          filtered.length
            ? 'bg-lighter-hover'
            : 'bg-lighter'}"
          onmouseenter={() => (active = filtered.length)}
          onclick={createFromQuery}
        >
          Add <span class="font-semibold">{query.trim()}</span>…
        </div>
      {/if}
      {#if optionCount === 0}
        <div class="no-results px-2 py-1.5 text-lightest-hover">
          {query.trim()
            ? "No results found"
            : hasRemote
              ? "Start typing to search…"
              : "No options"}
        </div>
      {/if}
    </div>
  {/if}
</div>
