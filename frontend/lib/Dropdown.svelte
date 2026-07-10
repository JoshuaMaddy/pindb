<script lang="ts">
  import type { Snippet } from "svelte";

  let {
    label,
    panelClass = "",
    trigger,
    children,
  }: {
    label: string;
    panelClass?: string;
    trigger: Snippet;
    children: Snippet;
  } = $props();

  let open = $state(false);
  let root: HTMLElement;

  $effect(() => {
    if (!open) return;
    const onDocClick = (evt: MouseEvent) => {
      if (evt.target instanceof Node && !root.contains(evt.target)) {
        open = false;
      }
    };
    const onKey = (evt: KeyboardEvent) => {
      if (evt.key === "Escape") open = false;
    };
    document.addEventListener("click", onDocClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("click", onDocClick);
      document.removeEventListener("keydown", onKey);
    };
  });
</script>

<div class="relative" bind:this={root}>
  <button
    type="button"
    class="flex items-center gap-1"
    aria-haspopup="true"
    aria-expanded={open}
    aria-label={label}
    onclick={() => (open = !open)}
  >
    {@render trigger()}
  </button>
  {#if open}
    <div
      data-dropdown-panel
      class="absolute right-0 top-full mt-1 z-50 bg-main border border-lightest rounded-lg p-3 flex flex-col gap-2 {panelClass}"
    >
      {@render children()}
    </div>
  {/if}
</div>
