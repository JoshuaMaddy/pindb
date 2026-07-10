<script lang="ts">
  import Columns3 from "@lucide/svelte/icons/columns-3";

  import Dropdown from "../../lib/Dropdown.svelte";

  // Successor of the Phase A pilot island: same localStorage key and checkbox
  // DOM contract (.col-toggle-check + data-col), but visibility is applied
  // reactively by the grid instead of poking style.display from outside.
  const STORAGE_KEY = "bulk_visible_cols";

  let {
    cols,
    visible = $bindable(),
  }: {
    cols: { key: string; label: string }[];
    visible: Record<string, boolean>;
  } = $props();

  export function loadSaved(): Record<string, boolean> {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}");
    } catch {
      return {};
    }
  }

  function toggle(col: string): void {
    visible[col] = !visible[col];
    const state = loadSaved();
    state[col] = visible[col];
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }
</script>

<Dropdown label="Toggle columns" panelClass="min-w-40">
  {#snippet trigger()}
    <Columns3 aria-hidden="true" />
    Columns
  {/snippet}
  {#each cols as col (col.key)}
    <label class="flex items-center gap-2 cursor-pointer font-semibold">
      <input
        type="checkbox"
        class="col-toggle-check"
        data-col={col.key}
        checked={visible[col.key]}
        onchange={() => toggle(col.key)}
      />
      {col.label}
    </label>
  {/each}
</Dropdown>
