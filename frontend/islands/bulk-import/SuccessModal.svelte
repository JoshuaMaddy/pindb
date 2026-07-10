<script lang="ts">
  import X from "@lucide/svelte/icons/x";

  export type SubmitResult = {
    results: {
      index: number;
      success: boolean;
      pin_id: number | null;
      pin_name: string | null;
      front_image_guid: string | null;
      error: string | null;
    }[];
    created_count: number;
    failed_count: number;
  };

  let {
    result,
    onClose,
  }: { result: SubmitResult; onClose: () => void } = $props();

  const title = $derived(
    `${result.created_count} pin(s) imported` +
      (result.failed_count ? `, ${result.failed_count} failed` : ""),
  );
</script>

<div
  id="success-modal"
  class="fixed inset-0 z-50 flex items-center justify-center bg-darker/80"
>
  <div
    class="bg-main border border-lightest rounded-xl p-6 max-w-2xl w-full max-h-[80vh] flex flex-col gap-4"
  >
    <div class="flex items-center justify-between">
      <h1 id="modal-title" class="text-lg font-bold sm:text-xl">{title}</h1>
      <button
        id="modal-close-btn"
        type="button"
        class="hover:text-accent"
        onclick={onClose}
      >
        <X />
      </button>
    </div>
    <div
      id="modal-grid"
      class="grid grid-cols-[repeat(auto-fill,minmax(120px,1fr))] gap-2 overflow-y-auto"
    >
      {#each result.results.filter((entry) => entry.success) as entry (entry.index)}
        <a
          href="/get/pin/{entry.pin_id}"
          class="flex flex-col gap-1 items-center border border-lightest rounded-lg p-2 hover:border-accent no-underline text-base-text text-center"
        >
          <div
            class="w-full aspect-square rounded"
            style="background:url('/get/image/{entry.front_image_guid}?w=200') center/cover"
          ></div>
          <span class="text-xs truncate w-full">{entry.pin_name ?? ""}</span>
        </a>
      {/each}
      {#if result.failed_count > 0}
        <p class="col-span-full text-sm text-error-main font-semibold">
          Failed rows remain in the table — fix errors and resubmit.
        </p>
      {/if}
    </div>
  </div>
</div>
