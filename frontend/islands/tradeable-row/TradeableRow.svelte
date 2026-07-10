<script lang="ts">
  // One owned-collection grade row: quantity, tradeable toggle + quantity,
  // remove. Each change PATCHes via htmx.ajax so the server re-renders the
  // whole panel content (outerHTML swap) — this island lives inside that
  // swap target, so the loader unmounts it on swap-out and mounts the fresh
  // generation on htmx:afterSwap.

  let {
    gradeName,
    quantity,
    tradeableQuantity,
    patchUrl,
    deleteUrl,
    targetId,
  }: {
    gradeName: string;
    quantity: number;
    tradeableQuantity: number;
    patchUrl: string;
    deleteUrl: string;
    targetId: string;
  } = $props();

  // svelte-ignore state_referenced_locally
  let maxQty = $state(Math.max(1, quantity));
  // svelte-ignore state_referenced_locally
  let tradeable = $state(tradeableQuantity > 0);
  // svelte-ignore state_referenced_locally
  let tradeableQty = $state(tradeableQuantity > 0 ? tradeableQuantity : 1);

  function patch(): void {
    window.htmx?.ajax("PATCH", patchUrl, {
      target: `#${targetId}`,
      swap: "outerHTML",
      values: {
        quantity: maxQty,
        tradeable_quantity: tradeable ? tradeableQty : 0,
      },
    });
  }

  function onQuantityChange(evt: Event): void {
    const input = evt.currentTarget as HTMLInputElement;
    maxQty = Math.max(1, parseInt(input.value, 10) || 1);
    tradeableQty = Math.min(tradeableQty, maxQty);
    patch();
  }

  function onTradeableQtyChange(evt: Event): void {
    const input = evt.currentTarget as HTMLInputElement;
    tradeableQty = Math.min(
      Math.max(1, parseInt(input.value, 10) || 1),
      maxQty,
    );
    patch();
  }

  function remove(): void {
    window.htmx?.ajax("DELETE", deleteUrl, {
      target: `#${targetId}`,
      swap: "outerHTML",
    });
  }
</script>

<div
  class="flex items-center gap-2 py-1.5 px-1 border-b border-lightest last:border-0"
>
  <span class="w-20 text-sm shrink-0">{gradeName}</span>
  <input
    type="number"
    value={maxQty}
    min="1"
    class="w-14 text-sm bg-lighter border border-lightest rounded px-1 py-0.5"
    title="Quantity owned"
    onchange={onQuantityChange}
  />
  <label
    class="flex items-center gap-1 text-sm cursor-pointer select-none shrink-0"
  >
    <input
      type="checkbox"
      bind:checked={tradeable}
      onchange={patch}
    />
    Trade
  </label>
  {#if tradeable}
    <input
      type="number"
      value={tradeableQty}
      min="1"
      max={maxQty}
      class="w-14 text-sm bg-lighter border border-lightest rounded px-1 py-0.5"
      title="Quantity tradeable"
      onchange={onTradeableQtyChange}
    />
  {/if}
  <button
    type="button"
    class="ml-auto shrink-0 text-lightest-hover hover:text-error-main-hover cursor-pointer bg-transparent border-0 text-lg leading-none"
    aria-label="Remove from collection"
    onclick={remove}
  >
    ×
  </button>
</div>
