<script lang="ts">
  import Copy from "@lucide/svelte/icons/copy";
  import Trash2 from "@lucide/svelte/icons/trash-2";

  import MultiSelect, { type Option } from "../../lib/MultiSelect.svelte";
  import { normalizeTagName, type TagRowData } from "./state.svelte";

  let {
    row = $bindable(),
    categories,
    siblingOptions,
    optionsBaseUrl,
    nameCheckUrl,
    onDuplicate,
    onDelete,
  }: {
    row: TagRowData;
    categories: Option[];
    siblingOptions: Option[];
    optionsBaseUrl: string;
    nameCheckUrl: string;
    onDuplicate: () => void;
    onDelete: () => void;
  } = $props();

  let nameFeedbackHtml = $state("");
  let nameCheckTimer: ReturnType<typeof setTimeout> | undefined;

  function scheduleNameCheck(): void {
    if (!nameCheckUrl) return;
    clearTimeout(nameCheckTimer);
    const name = normalizeTagName(row.name);
    nameCheckTimer = setTimeout(async () => {
      if (!name) {
        nameFeedbackHtml = "";
        return;
      }
      try {
        const response = await fetch(
          `${nameCheckUrl}?kind=tag&name=${encodeURIComponent(name)}`,
        );
        nameFeedbackHtml = response.ok ? await response.text() : "";
      } catch {
        nameFeedbackHtml = "";
      }
    }, 1000);
  }

  async function loadImplications(query: string): Promise<Option[]> {
    const params = new URLSearchParams({ q: query });
    const selfName = normalizeTagName(row.name);
    if (selfName) params.set("exclude_name", selfName);
    const response = await fetch(`${optionsBaseUrl}/tag?${params}`);
    if (!response.ok) return [];
    return response.json();
  }
</script>

<tr
  class="bulk-data-row border-b border-lightest {row.error ? 'row-error' : ''}"
  data-row-id={row.id}
  data-client-id={row.clientId}
  title={row.error ?? undefined}
>
  <td class="bulk-td">
    <div class="name-availability-field flex flex-col gap-1">
      <input
        type="text"
        required
        placeholder="tag_name"
        class="w-full bg-transparent border border-lightest rounded px-1 py-0.5"
        bind:value={row.name}
        oninput={scheduleNameCheck}
      />
      <div class="name-availability-feedback">
        {@html nameFeedbackHtml}
      </div>
    </div>
  </td>

  <td class="bulk-td">
    <MultiSelect
      bind:value={
        () => [row.category],
        (values) => (row.category = values[0] ?? "general")
      }
      options={categories}
      multiple={false}
      tagSingleMode={true}
    />
  </td>

  <td class="bulk-td">
    <MultiSelect
      value={row.implications}
      options={siblingOptions}
      multiple={true}
      tagMode={true}
      loadFn={loadImplications}
      onValueChange={(values) => (row.implications = values)}
    />
  </td>

  <td class="bulk-td">
    <MultiSelect
      value={row.aliases}
      multiple={true}
      create={true}
      onValueChange={(values) => (row.aliases = values)}
    />
  </td>

  <td class="bulk-td min-w-20" data-col-type="description">
    <textarea
      rows="1"
      class="w-full min-w-20 bg-transparent border border-lightest rounded px-1 py-0.5"
      bind:value={row.description}
    ></textarea>
  </td>

  <td class="bulk-td">
    <div class="flex gap-1 justify-center">
      <button
        type="button"
        class="dup-btn icon-btn"
        title="Duplicate row"
        onclick={onDuplicate}
      >
        <Copy />
      </button>
      <button
        type="button"
        class="del-btn icon-btn"
        title="Delete row"
        onclick={onDelete}
      >
        <Trash2 />
      </button>
    </div>
  </td>
</tr>
