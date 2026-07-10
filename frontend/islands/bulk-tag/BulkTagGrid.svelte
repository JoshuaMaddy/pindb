<script lang="ts">
  import LoaderCircle from "@lucide/svelte/icons/loader-circle";
  import Plus from "@lucide/svelte/icons/plus";
  import Tag from "@lucide/svelte/icons/tag";
  import Upload from "@lucide/svelte/icons/upload";
  import X from "@lucide/svelte/icons/x";

  import { dispatchToast } from "../../lib/toast";
  import type { Option } from "../../lib/MultiSelect.svelte";
  import BulkTagRow from "./BulkTagRow.svelte";
  import {
    newTagRow,
    normalizeTagName,
    toPayload,
    type TagRowData,
  } from "./state.svelte";

  type TagResult = {
    client_id: string;
    index: number;
    success: boolean;
    tag_id: number | null;
    tag_name: string | null;
    error: string | null;
  };
  type SubmitResult = {
    results: TagResult[];
    created_count: number;
    failed_count: number;
  };

  let {
    submitUrl,
    optionsBaseUrl,
    nameCheckUrl,
    categories,
  }: {
    submitUrl: string;
    optionsBaseUrl: string;
    nameCheckUrl: string;
    categories: Option[];
  } = $props();

  let rows = $state<TagRowData[]>([newTagRow(), newTagRow()]);
  let submitting = $state(false);
  let submitResult = $state<SubmitResult | null>(null);

  // In-batch rows double as implication options for their siblings; a
  // sibling's rename/category change flows through this derived list into
  // every other row's picker (MultiSelect.svelte diffs managed options).
  function siblingOptions(rowId: string): Option[] {
    return rows
      .filter((row) => row.id !== rowId && normalizeTagName(row.name))
      .map((row) => ({
        value: normalizeTagName(row.name),
        text: normalizeTagName(row.name),
        category: row.category || "general",
      }));
  }

  function duplicateRow(index: number): void {
    const source = rows[index];
    const copy = newTagRow();
    // Deliberately not name (duplicate risk) nor implications (cycle risk).
    copy.category = source.category;
    copy.description = source.description;
    rows.push(copy);
  }

  async function submit(): Promise<void> {
    let anyInvalid = false;
    const seen = new Map<string, number>();
    rows.forEach((row, index) => {
      const name = normalizeTagName(row.name);
      if (!name) {
        row.error = "Name is required";
        anyInvalid = true;
        return;
      }
      const firstIndex = seen.get(name);
      if (firstIndex !== undefined) {
        rows[firstIndex].error = "Duplicate name in batch";
        row.error = "Duplicate name in batch";
        anyInvalid = true;
        return;
      }
      seen.set(name, index);
      row.error = null;
    });
    if (anyInvalid) {
      dispatchToast("Fix highlighted rows before submitting.", "error");
      return;
    }

    submitting = true;
    try {
      const response = await fetch(submitUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tags: rows.map(toPayload) }),
      });
      if (!response.ok) {
        throw new Error(`Server error ${response.status}`);
      }
      const result: SubmitResult = await response.json();
      const byClientId = new Map(
        result.results.map((entry) => [entry.client_id, entry]),
      );
      for (const row of rows) {
        const entry = byClientId.get(row.clientId);
        if (entry && !entry.success) row.error = entry.error || "Failed";
      }
      rows = rows.filter((row) => {
        const entry = byClientId.get(row.clientId);
        return !entry || !entry.success;
      });
      if (!rows.length) rows.push(newTagRow());
      if (result.failed_count > 0) {
        dispatchToast(
          "Failed rows remain in the table — fix errors and resubmit.",
          "error",
        );
      } else {
        dispatchToast(
          `Created ${result.created_count} tag${
            result.created_count === 1 ? "" : "s"
          }.`,
          "success",
        );
      }
      submitResult = result;
    } catch (error) {
      dispatchToast(`Submit failed: ${String(error)}`, "error");
    } finally {
      submitting = false;
    }
  }
</script>

<div class="px-4 py-4 flex flex-col gap-2 h-full">
  <div class="flex items-center gap-2 flex-wrap">
    <h1 class="grow">Bulk Create Tags</h1>
    <button
      type="button"
      id="bulk-tag-add-row"
      class="flex items-center gap-1"
      onclick={() => rows.push(newTagRow())}
    >
      <Plus aria-hidden="true" /> Add Row
    </button>
    <button
      type="button"
      id="bulk-tag-submit"
      class="flex items-center gap-1 border-accent text-accent"
      disabled={submitting}
      onclick={() => void submit()}
    >
      {#if submitting}
        <LoaderCircle class="animate-spin" aria-hidden="true" />
      {:else}
        <Upload aria-hidden="true" />
      {/if}
      <span id="bulk-tag-submit-label">Submit ({rows.length})</span>
    </button>
  </div>
  <hr />
  <div class="overflow-x-auto overflow-y-clip rounded-lg border border-lightest">
    <table class="bulk-tag-table w-full border-collapse text-sm">
      <thead>
        <tr class="border-b border-lightest">
          <th class="bulk-th" data-col-type="name">Name *</th>
          <th class="bulk-th" data-col-type="category">Category</th>
          <th class="bulk-th" data-col-type="implications">Child of</th>
          <th class="bulk-th" data-col-type="aliases">Aliases</th>
          <th class="bulk-th min-w-20" data-col-type="description">
            Description
          </th>
          <th class="bulk-th">Actions</th>
        </tr>
      </thead>
      <tbody id="bulk-tag-tbody">
        {#each rows as row, index (row.id)}
          <BulkTagRow
            bind:row={rows[index]}
            {categories}
            siblingOptions={siblingOptions(row.id)}
            {optionsBaseUrl}
            {nameCheckUrl}
            onDuplicate={() => duplicateRow(index)}
            onDelete={() => rows.splice(index, 1)}
          />
        {/each}
      </tbody>
    </table>
  </div>
</div>
{#if submitResult}
  <div
    id="bulk-tag-success-modal"
    class="fixed inset-0 z-50 flex items-center justify-center bg-darker/80"
  >
    <div
      class="bg-main border border-lightest rounded-xl p-6 max-w-2xl w-full max-h-[80vh] flex flex-col gap-4"
    >
      <div class="flex items-center justify-between">
        <h1 id="bulk-tag-modal-title" class="text-lg font-bold sm:text-xl">
          {submitResult.created_count} tag{submitResult.created_count === 1
            ? ""
            : "s"} created{submitResult.failed_count
            ? `, ${submitResult.failed_count} failed`
            : ""}
        </h1>
        <button
          id="bulk-tag-modal-close-btn"
          type="button"
          class="hover:text-accent"
          onclick={() => (submitResult = null)}
        >
          <X />
        </button>
      </div>
      <div
        id="bulk-tag-modal-grid"
        class="grid grid-cols-[repeat(auto-fill,minmax(120px,1fr))] gap-2 overflow-y-auto"
      >
        {#each submitResult.results.filter((entry) => entry.success) as entry (entry.client_id)}
          <a
            href="/get/tag/{entry.tag_id}"
            class="flex flex-col gap-1 items-center border border-lightest rounded-lg p-2 hover:border-accent no-underline text-base-text text-center"
          >
            <Tag class="w-8 h-8" />
            <span class="text-xs truncate w-full text-center"
              >{entry.tag_name ?? ""}</span
            >
          </a>
        {/each}
        {#if submitResult.failed_count > 0}
          <p class="col-span-full text-sm text-error-main font-semibold">
            Failed rows remain in the table — fix errors and resubmit.
          </p>
        {/if}
      </div>
    </div>
  </div>
{/if}
