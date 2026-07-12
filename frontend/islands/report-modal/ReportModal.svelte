<script lang="ts">
  import Flag from "@lucide/svelte/icons/flag";
  import X from "@lucide/svelte/icons/x";

  import { dispatchToast } from "../../lib/toast";

  // Reports a piece of content to the admin queue. The length gate here is UX
  // only — routes/report.py re-checks it, and that check is the real one.

  let {
    postUrl,
    targetType,
    targetId,
    label = "Report",
    minLength = 10,
  }: {
    postUrl: string;
    targetType: string;
    targetId: number;
    label?: string;
    minLength?: number;
  } = $props();

  let open = $state(false);
  let reason = $state("");
  let submitting = $state(false);

  const trimmedLength = $derived(reason.trim().length);
  const remaining = $derived(minLength - trimmedLength);
  const canSubmit = $derived(trimmedLength >= minLength && !submitting);

  async function submit(): Promise<void> {
    submitting = true;
    try {
      const body = new FormData();
      body.append("target_type", targetType);
      body.append("target_id", String(targetId));
      body.append("reason", reason);
      const response = await fetch(postUrl, { method: "POST", body });
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail ?? "Could not send that report.");
      }
      open = false;
      reason = "";
      dispatchToast("Thanks — an admin will take a look.");
    } catch (error) {
      dispatchToast(
        error instanceof Error ? error.message : "Could not send that report.",
        "error",
      );
    } finally {
      submitting = false;
    }
  }
</script>

<div class="inline-flex items-center self-center">
  <button
    type="button"
    class="flex cursor-pointer items-center gap-1 rounded border border-lightest bg-transparent px-2 py-1 text-sm text-lightest-hover hover:border-error-dark hover:text-error-main"
    onclick={() => {
      open = true;
      reason = "";
    }}
  >
    <Flag class="h-4 w-4" />
    {label}
  </button>

  {#if open}
    <div
      class="fixed inset-0 z-50 flex items-center justify-center bg-darker/80"
      role="presentation"
      onclick={(evt) => {
        if (evt.target === evt.currentTarget) open = false;
      }}
    >
      <div
        class="relative mx-4 flex w-full max-w-lg flex-col gap-4 rounded-xl border border-lightest bg-main p-6 shadow-2xl"
      >
        <button
          type="button"
          class="absolute top-3 right-3 flex h-6 w-6 cursor-pointer items-center justify-center rounded border-0 bg-transparent text-lightest-hover hover:text-base-text"
          aria-label="Close"
          onclick={() => (open = false)}
        >
          <X class="h-4 w-4" />
        </button>
        <p class="text-base font-medium text-base-text">Report this content</p>
        <p class="text-sm text-lightest-hover">
          Tell us what's wrong with it. This goes to the site admins.
        </p>
        <label class="text-sm text-lightest-hover" for="report_reason">
          What's the problem?
        </label>
        <textarea
          id="report_reason"
          rows="5"
          required
          minlength={minLength}
          placeholder="This photo isn't a pin display — it's spam."
          class="w-full rounded-lg border border-lightest bg-darker px-3 py-2 text-base-text placeholder:text-lighter-hover focus:border-accent focus:outline-none"
          bind:value={reason}
          onkeydown={(evt) => {
            if (evt.key === "Escape") open = false;
          }}
        ></textarea>
        <p
          class="text-xs {trimmedLength >= minLength
            ? 'text-lightest-hover'
            : 'text-pending-main'}"
          aria-live="polite"
        >
          {trimmedLength >= minLength
            ? `${trimmedLength} characters`
            : `${remaining} more character${remaining === 1 ? "" : "s"} needed`}
        </p>
        <div class="flex justify-end gap-2 pt-2">
          <button
            type="button"
            class="flex cursor-pointer items-center gap-1 rounded border border-lightest bg-transparent px-2 py-1 text-base-text hover:border-accent"
            onclick={() => (open = false)}
          >
            Cancel
          </button>
          <button
            type="button"
            class="flex cursor-pointer items-center gap-1 rounded border border-error-dark bg-transparent px-2 py-1 text-error-main hover:bg-error-dark-hover disabled:cursor-not-allowed disabled:opacity-40"
            disabled={!canSubmit}
            onclick={submit}
          >
            Send report
          </button>
        </div>
      </div>
    </div>
  {/if}
</div>
