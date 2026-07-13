<script lang="ts">
  import ImagePlus from "@lucide/svelte/icons/image-plus";
  import LoaderCircle from "@lucide/svelte/icons/loader-circle";

  import { dispatchToast } from "../../lib/toast";
  import { transcodeToWebp } from "../../lib/webp";
  import DisplayImageTile from "./DisplayImageTile.svelte";
  import type { DisplayEditorProps, DisplayImage } from "./types";

  const WEBP_QUALITY = 95;

  const LAYOUTS: { value: string; label: string }[] = [
    { value: "grid", label: "Grid" },
    { value: "vertical", label: "Vertical" },
    { value: "carousel", label: "Carousel" },
  ];

  let {
    layout,
    maxImages,
    images: initialImages,
    uploadUrl,
    reorderUrl,
    updateDisplayUrl,
    imageBaseUrl,
    pinOptionsUrl,
    viewUrl,
    thumbUrlPrefix,
  }: DisplayEditorProps = $props();

  // Seeded from props once: islands remount on every HTMX swap, so props are
  // static for the life of a mount and this state is the source of truth after.
  // svelte-ignore state_referenced_locally
  let images = $state<DisplayImage[]>([...initialImages]);
  // svelte-ignore state_referenced_locally
  let currentLayout = $state(layout);
  let uploading = $state(0);
  let dragOver = $state(false);
  let dragFrom = $state<number | null>(null);
  let fileInput: HTMLInputElement;

  const isFull = $derived(images.length >= maxImages);

  async function uploadOne(file: File): Promise<void> {
    uploading += 1;
    try {
      const webpFile = await transcodeToWebp(file, WEBP_QUALITY);
      const body = new FormData();
      body.append("image", webpFile);
      const response = await fetch(uploadUrl, { method: "POST", body });
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail ?? `Upload failed (${response.status})`);
      }
      images.push((await response.json()) as DisplayImage);
    } catch (error) {
      dispatchToast(error instanceof Error ? error.message : "Upload failed", "error");
    } finally {
      uploading -= 1;
    }
  }

  // Sequential, one request per photo: `save_image` buffers the whole file, so
  // firing ten 20 MB uploads at once is the one way to make this hurt.
  async function uploadAll(files: FileList | File[]): Promise<void> {
    for (const file of Array.from(files)) {
      if (images.length + uploading >= maxImages) {
        dispatchToast(`A display holds at most ${maxImages} photos.`, "error");
        return;
      }
      if (!file.type.startsWith("image/")) continue;
      await uploadOne(file);
    }
  }

  async function persistUpdate(id: number, patch: FormData): Promise<void> {
    const response = await fetch(`${imageBaseUrl}/${id}`, {
      method: "POST",
      body: patch,
    });
    if (!response.ok) dispatchToast("Could not save that change.", "error");
  }

  async function persistOrder(): Promise<void> {
    const body = new FormData();
    for (const image of images) body.append("image_ids", String(image.id));
    const response = await fetch(reorderUrl, { method: "POST", body });
    if (!response.ok) dispatchToast("Could not save the new order.", "error");
  }

  async function removeImage(id: number): Promise<void> {
    const response = await fetch(`${imageBaseUrl}/${id}/delete`, {
      method: "POST",
    });
    if (!response.ok) {
      dispatchToast("Could not remove that photo.", "error");
      return;
    }
    images = images.filter((image) => image.id !== id);
  }

  async function changeLayout(next: string): Promise<void> {
    currentLayout = next;
    const body = new FormData();
    body.append("layout", next);
    const response = await fetch(updateDisplayUrl, { method: "POST", body });
    if (!response.ok) dispatchToast("Could not change the layout.", "error");
  }

  function onDragStart(index: number): void {
    dragFrom = index;
  }

  function onDragOver(index: number): void {
    if (dragFrom === null || dragFrom === index) return;
    const [moved] = images.splice(dragFrom, 1);
    images.splice(index, 0, moved);
    dragFrom = index;
  }

  function onDrop(): void {
    if (dragFrom === null) return;
    dragFrom = null;
    void persistOrder();
  }
</script>

<div class="flex flex-col gap-4">
  <div class="flex flex-wrap items-center gap-2">
    <span class="text-sm text-lightest-hover">Layout</span>
    {#each LAYOUTS as option (option.value)}
      <button
        type="button"
        class="cursor-pointer rounded border px-3 py-1 text-sm {currentLayout ===
        option.value
          ? 'border-accent text-accent'
          : 'border-lightest text-base-text hover:border-accent'}"
        aria-pressed={currentLayout === option.value}
        onclick={() => changeLayout(option.value)}
      >
        {option.label}
      </button>
    {/each}
    <a href={viewUrl} class="ml-auto text-sm text-accent">View my display →</a>
  </div>

  <div
    class="flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-6 text-center {dragOver
      ? 'border-accent'
      : 'border-lightest'} {isFull ? 'opacity-50' : 'cursor-pointer'}"
    role="button"
    tabindex="0"
    aria-label="Add display photos"
    ondragover={(evt) => {
      evt.preventDefault();
      dragOver = true;
    }}
    ondragleave={() => (dragOver = false)}
    ondrop={(evt) => {
      evt.preventDefault();
      dragOver = false;
      if (!isFull && evt.dataTransfer) void uploadAll(evt.dataTransfer.files);
    }}
    onclick={() => {
      if (!isFull) fileInput.click();
    }}
    onkeydown={(evt) => {
      if ((evt.key === "Enter" || evt.key === " ") && !isFull) fileInput.click();
    }}
  >
    <ImagePlus class="h-6 w-6 text-lightest-hover" />
    <p class="text-sm">
      {#if isFull}
        You've reached the {maxImages}-photo limit.
      {:else}
        Drop photos here, or click to choose. ({images.length}/{maxImages})
      {/if}
    </p>
    {#if uploading > 0}
      <span class="flex items-center gap-2 text-sm text-lightest-hover">
        <LoaderCircle class="h-4 w-4 animate-spin" />
        Uploading {uploading}…
      </span>
    {/if}
  </div>

  <!-- `multiple` is load-bearing: it is how several photos land at once, and the
       only way an e2e test can drive the upload via set_input_files. -->
  <input
    type="file"
    multiple
    class="hidden"
    accept="image/png,image/jpeg,image/jpg,image/webp"
    data-testid="display-image-input"
    bind:this={fileInput}
    onchange={() => {
      if (fileInput.files) void uploadAll(fileInput.files);
      fileInput.value = "";
    }}
  />

  {#if images.length > 0}
    <ul class="flex flex-col gap-2">
      {#each images as image, index (image.id)}
        <DisplayImageTile
          {image}
          {index}
          total={images.length}
          {thumbUrlPrefix}
          {pinOptionsUrl}
          showSizeControls={currentLayout === "grid"}
          onUpdate={persistUpdate}
          onDelete={removeImage}
          {onDragStart}
          {onDragOver}
          {onDrop}
          dragging={dragFrom === index}
        />
      {/each}
    </ul>
  {/if}
</div>
