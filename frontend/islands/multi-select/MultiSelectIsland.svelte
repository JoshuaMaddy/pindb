<script lang="ts">
  import MultiSelect, { type Option } from "../../lib/MultiSelect.svelte";

  // Enhancer island: adopts the server-rendered <select> next to its mount
  // point (templates render the island right after the select). The select
  // stays the form-submitting element — MultiSelect moves it inside itself,
  // keeps it in sync and dispatches real change events on it, so HTMX
  // triggers, form gates and form-persist saves keep working.

  let {
    selectId,
    loadUrl = "",
    create = false,
    tagMode = false,
    singleMode = false,
    placeholder = "",
  }: {
    selectId: string;
    loadUrl?: string;
    create?: boolean;
    tagMode?: boolean;
    singleMode?: boolean;
    placeholder?: string;
  } = $props();

  // Props are static per mount (islands remount on swap).
  // svelte-ignore state_referenced_locally
  const select = document.getElementById(
    selectId,
  ) as HTMLSelectElement | null;

  function readOption(option: HTMLOptionElement): Option {
    const out: Option = { value: option.value, text: option.text.trim() };
    if (option.dataset.category) out.category = option.dataset.category;
    if (option.dataset.icon) out.icon = option.dataset.icon;
    if (option.dataset.color) out.color = option.dataset.color;
    if (option.dataset.thumbnail) out.thumbnail = option.dataset.thumbnail;
    return out;
  }

  // Server-rendered options double as the local option pool; selected ones
  // seed the value. Static per mount by design.
  // svelte-ignore state_referenced_locally
  const options: Option[] = select
    ? Array.from(select.options).map(readOption)
    : [];
  let value = $state(
    select
      ? Array.from(select.selectedOptions).map((option) => option.value)
      : [],
  );
</script>

{#if select}
  <MultiSelect
    bind:value
    {options}
    multiple={select.multiple}
    {create}
    {tagMode}
    tagSingleMode={singleMode}
    {loadUrl}
    {placeholder}
    adoptedSelect={select}
  />
{/if}
