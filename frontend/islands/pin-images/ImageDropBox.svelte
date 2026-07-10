<script lang="ts">
  import type { Snippet } from "svelte";

  import { setInputFile, transcodeToWebp } from "../../lib/webp";

  let {
    inputId,
    previewId,
    existingUrl = null,
    pinField = "",
    stackClass = "",
    children,
  }: {
    inputId: string;
    previewId: string;
    existingUrl?: string | null;
    pinField?: string;
    stackClass?: string;
    children: Snippet;
  } = $props();

  // svelte-ignore state_referenced_locally
  let previewUrl = $state<string | null>(existingUrl);
  let accentBorder = $state(false);
  let hovered = false;

  function input(): HTMLInputElement | null {
    return document.getElementById(inputId) as HTMLInputElement | null;
  }

  async function acceptFile(file: File): Promise<void> {
    const target = input();
    if (!target) return;
    setInputFile(target, await transcodeToWebp(file));
    const final = target.files?.[0];
    if (!final) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
      previewUrl = String(evt.target?.result ?? "");
    };
    reader.readAsDataURL(final);
    // Form gates recompute on bubbling input; the island's own picker hook
    // listens for change, so dispatching input avoids re-entry.
    target.dispatchEvent(new Event("input", { bubbles: true }));
  }

  // The file input is server-rendered outside the island (its files ride the
  // normal form submit) — hook its picker changes here.
  $effect(() => {
    const target = input();
    if (!target) return;
    const onChange = () => {
      const file = target.files?.[0];
      if (file) void acceptFile(file);
    };
    target.addEventListener("change", onChange);
    const onPaste = (evt: ClipboardEvent) => {
      if (!hovered) return;
      for (const item of evt.clipboardData?.items ?? []) {
        if (item.type.startsWith("image/")) {
          const file = item.getAsFile();
          if (!file) continue;
          void acceptFile(file);
          evt.preventDefault();
          break;
        }
      }
    };
    document.addEventListener("paste", onPaste);
    return () => {
      target.removeEventListener("change", onChange);
      document.removeEventListener("paste", onPaste);
    };
  });
</script>

<div
  id={previewId}
  data-input-id={inputId}
  data-pin-field={pinField || undefined}
  class="image-drop w-full flex {stackClass} aspect-square justify-center items-center border-2 {accentBorder
    ? 'border-accent'
    : 'border-lightest'} rounded-lg bg-contain bg-no-repeat bg-center transition-all duration-100 cursor-pointer hover:border-accent"
  style={previewUrl ? `background-image: url('${previewUrl}')` : undefined}
  onclick={() => input()?.click()}
  onmouseenter={() => (hovered = true)}
  onmouseleave={() => (hovered = false)}
  ondragover={(evt) => {
    evt.preventDefault();
    accentBorder = true;
  }}
  ondragleave={() => (accentBorder = false)}
  ondrop={(evt) => {
    evt.preventDefault();
    accentBorder = true;
    const file = evt.dataTransfer?.files[0];
    if (file) void acceptFile(file);
  }}
  role="button"
  tabindex="0"
  onkeydown={(evt) => {
    if (evt.key === "Enter" || evt.key === " ") input()?.click();
  }}
>
  {#if !previewUrl}
    {@render children()}
  {/if}
</div>
