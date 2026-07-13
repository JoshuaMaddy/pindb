<script lang="ts">
  import GripVertical from "@lucide/svelte/icons/grip-vertical";
  import Trash2 from "@lucide/svelte/icons/trash-2";

  import MultiSelect from "../../lib/MultiSelect.svelte";
  import type { DisplayImage, ObjectFit, PinOption, SizeHint } from "./types";

  const CAPTION_DEBOUNCE_MS = 600;

  // Every shape is a rectangle a grid cell can actually cover — no 3-tile
  // option, since no rectangle spans exactly 3 cells. Mirrors
  // `_SPAN_CLASSES` in `templates/user/display_layouts.py`.
  const SIZES: { value: SizeHint; label: string; title: string }[] = [
    { value: "normal", label: "1×1", title: "Normal (1 tile)" },
    { value: "wide", label: "2×1", title: "Wide (2 tiles)" },
    { value: "tall", label: "1×2", title: "Tall (2 tiles)" },
    { value: "large", label: "2×2", title: "Large (4 tiles)" },
  ];

  // Unlike size, fit applies in every layout — it's how the photo fills
  // whatever box its layout gives it, not a grid-specific span.
  const FITS: { value: ObjectFit; label: string; title: string }[] = [
    { value: "cover", label: "Cover", title: "Cover — fills the box, cropped" },
    {
      value: "contain",
      label: "Contain",
      title: "Contain — whole photo visible, letterboxed",
    },
    { value: "fill", label: "Fill", title: "Fill — stretched to the box" },
  ];

  let {
    image,
    index,
    total,
    thumbUrlPrefix,
    pinOptionsUrl,
    showSizeControls,
    onUpdate,
    onDelete,
    onDragStart,
    onDragOver,
    onDrop,
    dragging,
  }: {
    image: DisplayImage;
    index: number;
    total: number;
    thumbUrlPrefix: string;
    pinOptionsUrl: string;
    showSizeControls: boolean;
    onUpdate: (id: number, patch: FormData) => Promise<void>;
    onDelete: (id: number) => void;
    onDragStart: (index: number) => void;
    onDragOver: (index: number) => void;
    onDrop: () => void;
    dragging: boolean;
  } = $props();

  // Seeded once from the prop; this component owns the field afterwards.
  // svelte-ignore state_referenced_locally
  let caption = $state(image.caption);
  // svelte-ignore state_referenced_locally
  let pinIds = $state<string[]>(image.pins.map((pin) => pin.value));

  let captionTimer: ReturnType<typeof setTimeout> | undefined;

  function saveCaption(): void {
    const body = new FormData();
    body.append("caption", caption);
    void onUpdate(image.id, body);
  }

  function onCaptionInput(): void {
    clearTimeout(captionTimer);
    captionTimer = setTimeout(saveCaption, CAPTION_DEBOUNCE_MS);
  }

  function setSize(next: SizeHint): void {
    image.sizeHint = next;
    const body = new FormData();
    body.append("size_hint", next);
    void onUpdate(image.id, body);
  }

  function setFit(next: ObjectFit): void {
    image.objectFit = next;
    const body = new FormData();
    body.append("object_fit", next);
    void onUpdate(image.id, body);
  }

  function savePins(values: string[]): void {
    const body = new FormData();
    if (values.length === 0) {
      // A FormData key with zero values sends nothing at all, which the server
      // reads as "field absent — leave the pins alone". One empty string is how
      // we say "explicitly none", so removing the last pin actually sticks.
      body.append("pin_ids", "");
    } else {
      for (const value of values) body.append("pin_ids", value);
    }
    void onUpdate(image.id, body);
  }

  async function loadPinOptions(query: string): Promise<PinOption[]> {
    const response = await fetch(
      `${pinOptionsUrl}?q=${encodeURIComponent(query)}`,
    );
    if (!response.ok) return [];
    return (await response.json()) as PinOption[];
  }
</script>

<li
  class="flex flex-col gap-2 rounded-lg border border-lightest bg-main p-3 sm:flex-row sm:items-start sm:gap-4"
  class:opacity-50={dragging}
  draggable="true"
  ondragstart={() => onDragStart(index)}
  ondragover={(evt) => {
    evt.preventDefault();
    onDragOver(index);
  }}
  ondrop={(evt) => {
    evt.preventDefault();
    onDrop();
  }}
  ondragend={() => onDrop()}
>
  <div class="flex items-center gap-2 shrink-0">
    <span
      class="cursor-grab text-lightest-hover"
      aria-label="Drag to reorder"
      title="Drag to reorder"
    >
      <GripVertical class="h-5 w-5" />
    </span>
    <img
      src={`${thumbUrlPrefix}${image.guid}?w=200`}
      alt={caption || `Display photo ${index + 1} of ${total}`}
      class="h-24 w-24 rounded object-cover"
      loading="lazy"
      decoding="async"
    />
  </div>

  <div class="flex min-w-0 flex-1 flex-col gap-2">
    <input
      type="text"
      bind:value={caption}
      oninput={onCaptionInput}
      onblur={saveCaption}
      maxlength="200"
      placeholder="Caption (optional)"
      aria-label="Caption"
      class="w-full rounded border border-lightest bg-darker px-2 py-1 text-base-text focus:border-accent focus:outline-none"
    />

    <MultiSelect
      bind:value={pinIds}
      options={image.pins}
      multiple
      placeholder="Pins in this photo…"
      loadFn={loadPinOptions}
      onValueChange={savePins}
    />
  </div>

  <div class="flex shrink-0 flex-col items-end gap-1.5">
    {#if showSizeControls}
      <div class="flex gap-1" role="group" aria-label="Tile size">
        {#each SIZES as size (size.value)}
          <button
            type="button"
            class="cursor-pointer rounded border px-1.5 py-1 text-xs {image.sizeHint ===
            size.value
              ? 'border-accent text-accent'
              : 'border-lightest text-base-text hover:border-accent'}"
            aria-pressed={image.sizeHint === size.value}
            title={size.title}
            onclick={() => setSize(size.value)}
          >
            {size.label}
          </button>
        {/each}
      </div>
    {/if}
    <div class="flex gap-1" role="group" aria-label="Image fit">
      {#each FITS as fit (fit.value)}
        <button
          type="button"
          class="cursor-pointer rounded border px-1.5 py-1 text-xs {image.objectFit ===
          fit.value
            ? 'border-accent text-accent'
            : 'border-lightest text-base-text hover:border-accent'}"
          aria-pressed={image.objectFit === fit.value}
          title={fit.title}
          onclick={() => setFit(fit.value)}
        >
          {fit.label}
        </button>
      {/each}
    </div>
    <button
      type="button"
      class="cursor-pointer rounded border border-error-dark p-1.5 text-error-main hover:border-error-dark-hover"
      title="Remove photo"
      onclick={() => onDelete(image.id)}
    >
      <Trash2 class="h-4 w-4" />
    </button>
  </div>
</li>
