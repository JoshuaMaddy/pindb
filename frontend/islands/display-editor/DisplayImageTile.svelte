<script lang="ts">
  import GripVertical from "@lucide/svelte/icons/grip-vertical";
  import Trash2 from "@lucide/svelte/icons/trash-2";
  import Maximize2 from "@lucide/svelte/icons/maximize-2";

  import MultiSelect from "../../lib/MultiSelect.svelte";
  import type { DisplayImage, PinOption, SizeHint } from "./types";

  const CAPTION_DEBOUNCE_MS = 600;

  let {
    image,
    index,
    total,
    thumbUrlPrefix,
    pinOptionsUrl,
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

  <div class="flex shrink-0 items-center gap-2">
    <button
      type="button"
      class="cursor-pointer rounded border p-1.5 {image.sizeHint === 'feature'
        ? 'border-accent text-accent'
        : 'border-lightest text-base-text hover:border-accent'}"
      aria-pressed={image.sizeHint === "feature"}
      title="Feature this photo (spans two columns)"
      onclick={() => setSize(image.sizeHint === "feature" ? "normal" : "feature")}
    >
      <Maximize2 class="h-4 w-4" />
    </button>
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
