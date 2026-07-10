<script lang="ts">
  import type { GradeEntry } from "./state.svelte";

  let {
    grades = $bindable(),
    colspan,
  }: { grades: GradeEntry[]; colspan: number } = $props();
</script>

<tr class="grades-sub-row bg-main-hover">
  <td class="bulk-td" {colspan}>
    <div class="bulk-sticky-center flex flex-col gap-2 p-2">
      {#each grades as grade, index (index)}
        <div class="flex items-center gap-2">
          <input
            type="text"
            class="bulk-input flex-1"
            placeholder="Grade"
            bind:value={grade.name}
          />
          <input
            type="number"
            class="bulk-input w-28"
            step="0.01"
            min="0"
            placeholder="Price"
            bind:value={grade.price}
          />
          {#if grades.length > 1}
            <button
              type="button"
              class="remove-grade-button"
              onclick={() => {
                grades.splice(index, 1);
              }}
            >
              Remove
            </button>
          {/if}
        </div>
      {/each}
      <button
        type="button"
        class="w-full"
        onclick={() => grades.push({ name: "", price: "" })}
      >
        Add Grade
      </button>
    </div>
  </td>
</tr>
