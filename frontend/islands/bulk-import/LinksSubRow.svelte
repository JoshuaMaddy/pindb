<script lang="ts">
  let {
    links = $bindable(),
    colspan,
  }: { links: string[]; colspan: number } = $props();
</script>

<tr class="links-sub-row bg-main-hover">
  <td class="bulk-td" {colspan}>
    <div class="bulk-sticky-center flex flex-col gap-2 p-2">
      {#each links as _link, index (index)}
        <div class="flex items-center gap-2">
          <input
            type="text"
            class="bulk-input flex-1"
            placeholder="https://..."
            bind:value={links[index]}
          />
          {#if links.length > 1}
            <button
              type="button"
              class="remove-link-button"
              onclick={() => {
                links.splice(index, 1);
              }}
            >
              Remove
            </button>
          {/if}
        </div>
      {/each}
      <button type="button" class="w-full" onclick={() => links.push("")}>
        Add Another Link
      </button>
    </div>
  </td>
</tr>
