<script lang="ts">
  import X from "@lucide/svelte/icons/x";

  let {
    triggerHtml,
    expectedUsername,
    formAction,
  }: {
    triggerHtml: string;
    expectedUsername: string;
    formAction: string;
  } = $props();

  let open = $state(false);
  let typed = $state("");
  let root: HTMLElement;

  $effect(() => {
    window.lucide?.createIcons({ nodes: [root] });
  });
</script>

<div class="inline-flex items-center self-start" bind:this={root}>
  <!-- The server-rendered trigger is itself interactive (a real button);
       a role on this wrapper would prune it from the accessibility tree. -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="inline-flex items-center"
    onclick={() => {
      open = true;
      typed = "";
    }}
  >
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
        class="relative bg-main border border-lightest rounded-xl shadow-2xl p-6 max-w-md w-full mx-4 flex flex-col gap-4"
      >
        <button
          type="button"
          class="absolute top-3 right-3 flex items-center justify-center w-6 h-6 rounded border-0 bg-transparent cursor-pointer text-lightest-hover hover:text-base-text"
          aria-label="Close"
          onclick={() => (open = false)}
        >
          <X class="w-4 h-4" />
        </button>
        <p class="text-base font-medium text-base-text">
          Delete your account permanently?
        </p>
        <p class="text-sm text-lightest-hover">
          This removes your profile, sessions, linked sign-in providers,
          favorites, collection and want lists, and personal pin sets. Audit
          history that referred to you will be anonymized. This cannot be
          undone.
        </p>
        <form method="post" action={formAction} class="flex flex-col gap-4">
          <div class="flex flex-col gap-2">
            <label class="text-sm text-lightest-hover" for="confirm_username">
              Type your username to confirm:
            </label>
            <input
              type="text"
              id="confirm_username"
              name="confirm_username"
              autocomplete="off"
              class="w-full px-3 py-2 rounded-lg border border-lightest bg-darker text-base-text placeholder:text-lighter-hover focus:outline-none focus:border-accent"
              placeholder={expectedUsername}
              bind:value={typed}
              onkeydown={(evt) => {
                if (evt.key === "Escape") open = false;
              }}
            />
          </div>
          <div class="flex gap-2 justify-end">
            <button
              type="button"
              class="flex items-center gap-1 px-3 py-1.5 rounded border border-lightest bg-transparent cursor-pointer text-base-text hover:border-accent"
              onclick={() => (open = false)}
            >
              Cancel
            </button>
            <button
              type="submit"
              class="flex items-center gap-1 px-3 py-1.5 rounded border border-error-dark bg-transparent text-error-main hover:bg-error-dark-hover disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent"
              disabled={typed !== expectedUsername}
            >
              Delete my account
            </button>
          </div>
        </form>
      </div>
    </div>
  {/if}
</div>
