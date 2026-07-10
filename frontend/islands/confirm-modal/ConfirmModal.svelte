<script lang="ts">
  import X from "@lucide/svelte/icons/x";

  // Confirmation modal around a server-rendered trigger. Exactly one of
  // formAction / hxDelete applies (validated server-side in
  // templates/components/dialogs/confirm_modal.py).

  let {
    triggerHtml,
    message,
    formAction = "",
    hxDelete = "",
    hxTarget = "",
    hxSwap = "outerHTML",
    confirmLabel = "Delete",
    htmxPost = false,
  }: {
    triggerHtml: string;
    message: string;
    formAction?: string;
    hxDelete?: string;
    hxTarget?: string;
    hxSwap?: string;
    confirmLabel?: string;
    htmxPost?: boolean;
  } = $props();

  let open = $state(false);
  let root: HTMLElement;

  // Server-rendered trigger may carry lucide placeholders; htmx-posting forms
  // rendered while open need htmx bindings.
  $effect(() => {
    window.lucide?.createIcons({ nodes: [root] });
  });
  $effect(() => {
    if (open) window.htmx?.process(root);
  });

  const confirmButtonClass =
    "flex items-center gap-1 px-2 py-1 rounded border border-error-dark " +
    "bg-transparent cursor-pointer text-error-main hover:bg-error-dark-hover";

  function confirmViaDelete(): void {
    window.htmx?.ajax("DELETE", hxDelete, {
      ...(hxTarget ? { target: hxTarget } : {}),
      swap: hxSwap,
    });
    open = false;
  }
</script>

<div class="inline-flex items-center self-center" bind:this={root}>
  <!-- The server-rendered trigger is itself interactive (a real button);
       a role on this wrapper would prune it from the accessibility tree. -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="inline-flex items-center" onclick={() => (open = true)}>
    {@html triggerHtml}
  </div>
  {#if open}
    <div
      class="fixed inset-0 z-50 flex items-center justify-center bg-darker/80"
      role="presentation"
      onclick={(evt) => {
        if (evt.target === evt.currentTarget) open = false;
      }}
    >
      <div
        class="relative bg-main border border-lightest rounded-xl shadow-2xl p-6 max-w-sm w-full mx-4 flex flex-col gap-4"
      >
        <button
          type="button"
          class="absolute top-3 right-3 flex items-center justify-center w-6 h-6 rounded border-0 bg-transparent cursor-pointer text-lightest-hover hover:text-base-text"
          aria-label="Close"
          onclick={() => (open = false)}
        >
          <X class="w-4 h-4" />
        </button>
        <p class="text-base">{message}</p>
        <div class="flex gap-2 justify-end">
          <button
            type="button"
            class="flex items-center gap-1 px-2 py-1 rounded border border-lightest bg-transparent cursor-pointer text-base-text hover:border-accent"
            onclick={() => (open = false)}
          >
            Cancel
          </button>
          {#if formAction}
            {#if htmxPost}
              <form
                method="post"
                action={formAction}
                {...{ "hx-post": formAction, "hx-swap": "none" }}
                data-htmx-submit-guard=""
              >
                <button type="submit" class={confirmButtonClass}>
                  {confirmLabel}
                </button>
              </form>
            {:else}
              <form method="post" action={formAction}>
                <button type="submit" class={confirmButtonClass}>
                  {confirmLabel}
                </button>
              </form>
            {/if}
          {:else}
            <button
              type="button"
              class={confirmButtonClass}
              onclick={confirmViaDelete}
            >
              {confirmLabel}
            </button>
          {/if}
        </div>
      </div>
    </div>
  {/if}
</div>
