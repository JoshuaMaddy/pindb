<script lang="ts">
  import X from "@lucide/svelte/icons/x";

  // Modal around a server-rendered trigger that collects the reviewer's change
  // request. The length gate here is UX only — routes/approve.py re-checks it.

  let {
    triggerHtml,
    formAction,
    entityLabel,
    minLength = 25,
    hxTarget = "#pending-content",
    hxSwap = "outerHTML",
  }: {
    triggerHtml: string;
    formAction: string;
    entityLabel: string;
    minLength?: number;
    hxTarget?: string;
    hxSwap?: string;
  } = $props();

  let open = $state(false);
  let reason = $state("");
  let root: HTMLElement;

  const trimmedLength = $derived(reason.trim().length);
  const remaining = $derived(minLength - trimmedLength);
  const canSubmit = $derived(trimmedLength >= minLength);

  // The trigger arrives as raw HTML and may carry lucide placeholders; the form
  // is only in the DOM while open, so htmx has to bind it on each open.
  $effect(() => {
    window.lucide?.createIcons({ nodes: [root] });
  });
  $effect(() => {
    if (open) window.htmx?.process(root);
  });
</script>

<div class="inline-flex items-center self-center" bind:this={root}>
  <!-- The server-rendered trigger is itself interactive (a real button);
       a role on this wrapper would prune it from the accessibility tree. -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="inline-flex items-center"
    onclick={() => {
      open = true;
      reason = "";
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
        class="relative bg-main border border-lightest rounded-xl shadow-2xl p-6 max-w-lg w-full mx-4 flex flex-col gap-4"
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
          Request changes to {entityLabel}
        </p>
        <p class="text-sm text-lightest-hover">
          This goes to whoever submitted it, so say what needs to change and how.
          They can edit the entry and resubmit it for review. Markdown is
          supported.
        </p>
        <form
          method="post"
          action={formAction}
          class="flex flex-col gap-2"
          {...{
            "hx-post": formAction,
            "hx-target": hxTarget,
            "hx-swap": hxSwap,
          }}
          data-htmx-submit-guard=""
        >
          <label class="text-sm text-lightest-hover" for="change_request_reason">
            What needs to change?
          </label>
          <textarea
            id="change_request_reason"
            name="reason"
            rows="5"
            required
            minlength={minLength}
            placeholder="The front image is blurry — please re-upload a sharper photo taken straight on."
            class="w-full px-3 py-2 rounded-lg border border-lightest bg-darker text-base-text placeholder:text-lighter-hover focus:outline-none focus:border-accent"
            bind:value={reason}
            onkeydown={(evt) => {
              if (evt.key === "Escape") open = false;
            }}
          ></textarea>
          <p
            class="text-xs {canSubmit
              ? 'text-lightest-hover'
              : 'text-pending-main'}"
            aria-live="polite"
          >
            {canSubmit
              ? `${trimmedLength} characters`
              : `${remaining} more character${remaining === 1 ? "" : "s"} needed`}
          </p>
          <div class="flex gap-2 justify-end pt-2">
            <button
              type="button"
              class="flex items-center gap-1 px-2 py-1 rounded border border-lightest bg-transparent cursor-pointer text-base-text hover:border-accent"
              onclick={() => (open = false)}
            >
              Cancel
            </button>
            <button
              type="submit"
              class="flex items-center gap-1 px-2 py-1 rounded border border-pending-dark bg-transparent cursor-pointer text-pending-main hover:bg-pending-dark-hover disabled:opacity-40 disabled:cursor-not-allowed"
              disabled={!canSubmit}
            >
              Request changes
            </button>
          </div>
        </form>
      </div>
    </div>
  {/if}
</div>
