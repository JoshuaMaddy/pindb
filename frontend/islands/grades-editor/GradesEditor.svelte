<script lang="ts">
  import {
    notifyFormOfRestore,
    persistedStringList,
    readPersistedFields,
  } from "../../lib/form-persist";

  type GradeRow = { id: string; name: string; price: string };

  let { grades }: { grades: GradeRow[] } = $props();

  // Island props are static per mount — initial-value capture is intended.
  // svelte-ignore state_referenced_locally
  let rows = $state<GradeRow[]>(grades.map((row) => ({ ...row })));

  let addButton: HTMLButtonElement;

  // Reload restore: the legacy form_persist script saves all named fields
  // (including ours); we restore our own because its generic restore skips
  // [data-island] subtrees.
  $effect(() => {
    const fields = readPersistedFields();
    const names = persistedStringList(fields, "grade_names");
    if (!names?.length) return;
    const prices = persistedStringList(fields, "grade_prices");
    rows = names.map((name, index) => ({
      id: crypto.randomUUID(),
      name,
      price: prices?.[index] ?? "",
    }));
    notifyFormOfRestore(addButton);
  });

  function addRow(): void {
    rows.push({ id: crypto.randomUUID(), name: "", price: "" });
  }

  function removeRow(id: string): void {
    rows = rows.filter((row) => row.id !== id);
    notifyFormOfRestore(addButton);
  }
</script>

{#each rows as row (row.id)}
  <div class="flex min-w-0 flex-col gap-2 sm:flex-row sm:flex-nowrap sm:items-center">
    <input
      class="w-full min-w-0 sm:w-auto sm:min-w-0 sm:flex-1"
      type="text"
      name="grade_names"
      bind:value={row.name}
      required
      autocomplete="off"
      placeholder="Grade"
    />
    <input
      class="w-full min-w-0 sm:w-25"
      type="number"
      name="grade_prices"
      bind:value={row.price}
      autocomplete="off"
      step="0.01"
      min="0"
      placeholder="Unknown"
    />
    {#if rows.length > 1}
      <button
        type="button"
        class="remove-grade-button w-full sm:w-auto sm:shrink-0"
        onclick={() => removeRow(row.id)}
      >
        Remove
      </button>
    {/if}
  </div>
{/each}
<button type="button" class="w-full" bind:this={addButton} onclick={addRow}>
  Add Grade
</button>
