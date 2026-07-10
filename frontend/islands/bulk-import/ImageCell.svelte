<script lang="ts">
  import LoaderCircle from "@lucide/svelte/icons/loader-circle";

  import { transcodeToWebp } from "../../lib/webp";

  const BULK_IMAGE_WEBP_QUALITY = 95;

  let {
    side,
    rowId,
    guid = $bindable(null),
    uploadImageUrl,
  }: {
    side: "front" | "back";
    rowId: string;
    guid?: string | null;
    uploadImageUrl: string;
  } = $props();

  let previewUrl = $state<string | null>(null);
  let uploading = $state(false);
  let failed = $state(false);
  let accent = $state(false);
  let hovered = false;
  let fileInput: HTMLInputElement;

  // Paste-anywhere: an image pasted while this cell is hovered uploads here.
  $effect(() => {
    const onPaste = (evt: ClipboardEvent) => {
      if (!hovered) return;
      for (const item of evt.clipboardData?.items ?? []) {
        if (item.type.startsWith("image/")) {
          const file = item.getAsFile();
          if (!file) continue;
          void upload(file);
          evt.preventDefault();
          break;
        }
      }
    };
    document.addEventListener("paste", onPaste);
    return () => document.removeEventListener("paste", onPaste);
  });

  // Draft-restored rows arrive with a guid but no local preview — show the
  // stored image.
  $effect(() => {
    if (guid && !previewUrl) previewUrl = `/get/image/${guid}?w=200`;
    if (!guid && previewUrl?.startsWith("/get/image/")) previewUrl = null;
  });

  export async function upload(file: File): Promise<void> {
    uploading = true;
    failed = false;
    try {
      const webpFile = await transcodeToWebp(file, BULK_IMAGE_WEBP_QUALITY);
      const formData = new FormData();
      formData.append("image", webpFile);
      const response = await fetch(uploadImageUrl, {
        method: "POST",
        body: formData,
      });
      if (!response.ok) throw new Error(`upload failed ${response.status}`);
      const payload = await response.json();
      guid = String(payload.guid);
      const reader = new FileReader();
      reader.onload = (evt) => {
        previewUrl = String(evt.target?.result ?? "");
      };
      reader.readAsDataURL(webpFile);
      accent = true;
    } catch {
      failed = true;
      guid = null;
    } finally {
      uploading = false;
    }
  }
</script>

<div class="relative">
  <div
    class="image-drop-cell"
    data-row={rowId}
    data-side={side}
    style="width:72px;height:72px;border:2px dashed {accent
      ? 'var(--color-accent)'
      : 'var(--color-lightest)'};border-radius:8px;display:flex;align-items:center;justify-content:center;cursor:pointer;background-size:contain;background-repeat:no-repeat;background-position:center;font-size:10px;text-align:center;padding:4px;{previewUrl
      ? `background-image:url('${previewUrl}');`
      : ''}"
    role="button"
    tabindex="0"
    onclick={() => fileInput.click()}
    onkeydown={(evt) => {
      if (evt.key === "Enter" || evt.key === " ") fileInput.click();
    }}
    onmouseenter={() => (hovered = true)}
    onmouseleave={() => (hovered = false)}
    ondragover={(evt) => {
      evt.preventDefault();
      accent = true;
    }}
    ondragleave={() => {
      if (!previewUrl) accent = false;
    }}
    ondrop={(evt) => {
      evt.preventDefault();
      const file = evt.dataTransfer?.files[0];
      if (file) void upload(file);
    }}
  >
    {#if !previewUrl}
      {failed ? "Upload failed" : side === "front" ? "Front" : "Back"}
    {/if}
  </div>
  <input
    type="file"
    class="img-file-input hidden"
    data-row={rowId}
    data-side={side}
    accept="image/png,image/jpeg,image/jpg,image/webp"
    bind:this={fileInput}
    onchange={() => {
      const file = fileInput.files?.[0];
      if (file) void upload(file);
    }}
  />
  {#if uploading}
    <div
      class="img-spinner absolute inset-0 flex items-center justify-center bg-darker rounded"
      data-row={rowId}
      data-side={side}
    >
      <LoaderCircle class="animate-spin" />
    </div>
  {/if}
</div>
