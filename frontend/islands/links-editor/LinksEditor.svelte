<script lang="ts">
  import {
    notifyFormOfRestore,
    persistedStringList,
    readPersistedFields,
  } from "../../lib/form-persist";

  let {
    links,
    placeholder = "",
    addButtonId = "",
  }: { links: string[]; placeholder?: string; addButtonId?: string } = $props();

  type LinkRow = { id: string; path: string };

  // svelte-ignore state_referenced_locally
  let rows = $state<LinkRow[]>(
    links.map((path) => ({ id: crypto.randomUUID(), path })),
  );

  let addButton: HTMLButtonElement;

  // Reload restore — see GradesEditor.
  $effect(() => {
    const restored = persistedStringList(readPersistedFields(), "links");
    if (!restored?.length) return;
    rows = restored.map((path) => ({ id: crypto.randomUUID(), path }));
    notifyFormOfRestore(addButton);
  });

  function addRow(): void {
    rows.push({ id: crypto.randomUUID(), path: "" });
  }

  function removeRow(id: string): void {
    rows = rows.filter((row) => row.id !== id);
    notifyFormOfRestore(addButton);
  }
</script>

{#each rows as row (row.id)}
  <div class="grid grid-cols-[1fr_min-content] gap-2 mb-2">
    <input
      type="text"
      name="links"
      bind:value={row.path}
      autocomplete="off"
      placeholder={placeholder || undefined}
      class="col-span-1"
    />
    {#if rows.length > 1}
      <button
        type="button"
        class="remove-link-button"
        onclick={() => removeRow(row.id)}
      >
        Remove
      </button>
    {/if}
  </div>
{/each}
<button
  type="button"
  class="w-full mt-2"
  id={addButtonId || undefined}
  bind:this={addButton}
  onclick={addRow}
>
  Add Another Link
</button>
