<script lang="ts">
  import ClipboardPaste from "@lucide/svelte/icons/clipboard-paste";
  import Copy from "@lucide/svelte/icons/copy";
  import Trash2 from "@lucide/svelte/icons/trash-2";

  import MultiSelect, { type Option } from "../../lib/MultiSelect.svelte";
  import ImageCell from "./ImageCell.svelte";
  import type { BulkRowData, EntityType } from "./state.svelte";

  let {
    row = $bindable(),
    ref,
    localOptions,
    visible,
    clipboardType,
    nameMinWidth,
    gradesOpen,
    linksOpen,
    onToggleGrades,
    onToggleLinks,
    onDuplicate,
    onDelete,
    onCopy,
    onPaste,
    onOptionCreate,
  }: {
    row: BulkRowData;
    ref: {
      uploadImageUrl: string;
      optionsBaseUrl: string;
      nameCheckUrl: string;
      currencies: Option[];
      acquisitionTypes: Option[];
      fundingTypes: Option[];
      magnitudeInputPattern: string;
    };
    localOptions: Record<EntityType, Option[]>;
    visible: Record<string, boolean>;
    clipboardType: string | null;
    nameMinWidth: string;
    gradesOpen: boolean;
    linksOpen: boolean;
    onToggleGrades: () => void;
    onToggleLinks: () => void;
    onDuplicate: () => void;
    onDelete: () => void;
    onCopy: (colType: string) => void;
    onPaste: (colType: string) => void;
    onOptionCreate: (entityType: EntityType, option: Option) => void;
  } = $props();

  let nameFeedbackHtml = $state("");
  let nameCheckTimer: ReturnType<typeof setTimeout> | undefined;

  function scheduleNameCheck(): void {
    if (!ref.nameCheckUrl) return;
    clearTimeout(nameCheckTimer);
    const name = row.name;
    nameCheckTimer = setTimeout(async () => {
      if (!name.trim()) {
        nameFeedbackHtml = "";
        return;
      }
      try {
        const response = await fetch(
          `${ref.nameCheckUrl}?kind=pin&name=${encodeURIComponent(name)}`,
        );
        nameFeedbackHtml = response.ok ? await response.text() : "";
      } catch {
        nameFeedbackHtml = "";
      }
    }, 1000);
  }

  const gradesCount = $derived(
    row.grades.filter((grade) => grade.name).length,
  );
  const linksCount = $derived(
    row.links.filter((link) => link.trim()).length,
  );

  function hiddenStyle(col: string): string {
    return visible[col] === false ? "display: none;" : "";
  }
</script>

{#snippet copyPaste(colType: string)}
  <button
    type="button"
    class="cell-copy-btn"
    title="Copy"
    onclick={() => onCopy(colType)}
  >
    <Copy />
  </button>
  <button
    type="button"
    class="cell-paste-btn"
    title="Paste"
    onclick={() => onPaste(colType)}
  >
    <ClipboardPaste />
  </button>
{/snippet}

{#snippet multiCell(
  colType: string,
  entityType: EntityType,
  field: "shops" | "tags" | "artists" | "pinSets",
  dataCol: string | null,
)}
  <td
    class="bulk-td relative copyable-cell {clipboardType === colType
      ? 'has-clipboard'
      : ''}"
    data-col-type={colType}
    data-col={dataCol}
    style={dataCol ? hiddenStyle(dataCol) : ""}
  >
    <MultiSelect
      value={row[field].map((option) => option.value)}
      options={localOptions[entityType]}
      multiple={true}
      create={true}
      tagMode={entityType === "tag"}
      loadUrl="{ref.optionsBaseUrl}/{entityType}"
      onValueChange={(_values, selected) => {
        row[field] = selected;
      }}
      onOptionCreate={(option) => onOptionCreate(entityType, option)}
    />
    {@render copyPaste(colType)}
  </td>
{/snippet}

<tr
  class="bulk-data-row border-b border-lightest {row.error ? 'row-error' : ''}"
  data-row-id={row.id}
  title={row.error ?? undefined}
>
  <td class="bulk-td bulk-sticky-td bulk-sticky-col-0 w-8 text-center">
    <input type="checkbox" class="row-checkbox" />
  </td>

  <td
    class="bulk-td bulk-sticky-td bulk-sticky-col-1"
    data-col-type="front_image"
    style="width:88px;min-width:88px;"
  >
    <ImageCell
      side="front"
      rowId={row.id}
      bind:guid={row.frontImageGuid}
      uploadImageUrl={ref.uploadImageUrl}
    />
  </td>

  <td class="bulk-td relative" data-col-type="back_image">
    <ImageCell
      side="back"
      rowId={row.id}
      bind:guid={row.backImageGuid}
      uploadImageUrl={ref.uploadImageUrl}
    />
  </td>

  <td
    class="bulk-td bulk-sticky-td bulk-sticky-col-2 copyable-cell {clipboardType ===
    'name'
      ? 'has-clipboard'
      : ''}"
    data-col-type="name"
    style="min-width: {nameMinWidth};"
  >
    <div class="name-availability-field flex flex-col gap-1">
      <input
        type="text"
        class="bulk-input w-full"
        data-row={row.id}
        data-field="name"
        placeholder="Pin name"
        autocomplete="off"
        bind:value={row.name}
        oninput={scheduleNameCheck}
      />
      <div class="name-availability-feedback">
        <!-- eslint-disable-next-line svelte/no-at-html-tags — server-authored fragment -->
        {@html nameFeedbackHtml}
      </div>
    </div>
    {@render copyPaste("name")}
  </td>

  {@render multiCell("shops", "shop", "shops", null)}

  <td
    class="bulk-td relative copyable-cell {clipboardType === 'acquisition_type'
      ? 'has-clipboard'
      : ''}"
    data-col-type="acquisition_type"
  >
    <MultiSelect
      bind:value={
        () => (row.acquisitionType ? [row.acquisitionType] : []),
        (values) => (row.acquisitionType = values[0] ?? "")
      }
      options={ref.acquisitionTypes}
      multiple={false}
    />
    {@render copyPaste("acquisition_type")}
  </td>

  <td
    class="bulk-td relative copyable-cell {clipboardType === 'grades'
      ? 'has-clipboard'
      : ''}"
    data-col-type="grades"
  >
    <button
      type="button"
      class="grades-toggle-btn w-full {gradesOpen
        ? 'border-accent text-accent'
        : ''}"
      onclick={onToggleGrades}
    >
      Grades (<span class="grades-count" data-row={row.id}>{gradesCount}</span
      >)
    </button>
    {@render copyPaste("grades")}
  </td>

  <td
    class="bulk-td relative copyable-cell {clipboardType === 'currency_id'
      ? 'has-clipboard'
      : ''}"
    data-col-type="currency_id"
  >
    <MultiSelect
      bind:value={
        () => (row.currencyId ? [row.currencyId] : []),
        (values) => (row.currencyId = values[0] ?? "")
      }
      options={ref.currencies}
      multiple={false}
    />
    {@render copyPaste("currency_id")}
  </td>

  {@render multiCell("tags", "tag", "tags", null)}
  {@render multiCell("artists", "artist", "artists", "artists")}
  {@render multiCell("pin_sets", "pin_set", "pinSets", "pin_sets")}

  <td
    class="bulk-td"
    data-col="limited_edition"
    data-col-type="limited_edition"
    style={hiddenStyle("limited_edition")}
  >
    <MultiSelect
      bind:value={
        () => (row.limitedEdition ? [row.limitedEdition] : []),
        (values) =>
          (row.limitedEdition = (values[0] ?? "") as "" | "true" | "false")
      }
      options={[
        { value: "true", text: "Yes" },
        { value: "false", text: "No" },
      ]}
      multiple={false}
      placeholder="—"
    />
  </td>

  <td
    class="bulk-td relative copyable-cell {clipboardType === 'number_produced'
      ? 'has-clipboard'
      : ''}"
    data-col="number_produced"
    data-col-type="number_produced"
    style={hiddenStyle("number_produced")}
  >
    <input
      type="number"
      class="bulk-input w-full"
      data-row={row.id}
      data-field="number_produced"
      min="0"
      step="1"
      placeholder="—"
      bind:value={row.numberProduced}
    />
    {@render copyPaste("number_produced")}
  </td>

  <td
    class="bulk-td relative copyable-cell {clipboardType === 'release_date'
      ? 'has-clipboard'
      : ''}"
    data-col="release_date"
    data-col-type="release_date"
    style={hiddenStyle("release_date")}
  >
    <input
      type="date"
      class="bulk-input w-full"
      data-row={row.id}
      data-field="release_date"
      bind:value={row.releaseDate}
    />
    {@render copyPaste("release_date")}
  </td>

  <td
    class="bulk-td relative copyable-cell {clipboardType === 'end_date'
      ? 'has-clipboard'
      : ''}"
    data-col="end_date"
    data-col-type="end_date"
    style={hiddenStyle("end_date")}
  >
    <input
      type="date"
      class="bulk-input w-full"
      data-row={row.id}
      data-field="end_date"
      bind:value={row.endDate}
    />
    {@render copyPaste("end_date")}
  </td>

  <td
    class="bulk-td relative copyable-cell {clipboardType === 'funding_type'
      ? 'has-clipboard'
      : ''}"
    data-col="funding_type"
    data-col-type="funding_type"
    style={hiddenStyle("funding_type")}
  >
    <MultiSelect
      bind:value={
        () => (row.fundingType ? [row.fundingType] : []),
        (values) => (row.fundingType = values[0] ?? "")
      }
      options={ref.fundingTypes}
      multiple={false}
      placeholder="—"
    />
    {@render copyPaste("funding_type")}
  </td>

  <td
    class="bulk-td relative copyable-cell {clipboardType === 'posts'
      ? 'has-clipboard'
      : ''}"
    data-col="posts"
    data-col-type="posts"
    style={hiddenStyle("posts")}
  >
    <input
      type="number"
      class="bulk-input w-full"
      data-row={row.id}
      data-field="posts"
      min="1"
      step="1"
      placeholder="1"
      bind:value={row.posts}
    />
    {@render copyPaste("posts")}
  </td>

  <td
    class="bulk-td relative copyable-cell {clipboardType === 'width'
      ? 'has-clipboard'
      : ''}"
    data-col="width"
    data-col-type="width"
    style={hiddenStyle("width")}
  >
    <input
      type="text"
      class="bulk-input w-full"
      data-row={row.id}
      data-field="width"
      pattern={ref.magnitudeInputPattern || undefined}
      autocomplete="off"
      placeholder="e.g. 40mm or 1.5in"
      bind:value={row.width}
    />
    {@render copyPaste("width")}
  </td>

  <td
    class="bulk-td relative copyable-cell {clipboardType === 'height'
      ? 'has-clipboard'
      : ''}"
    data-col="height"
    data-col-type="height"
    style={hiddenStyle("height")}
  >
    <input
      type="text"
      class="bulk-input w-full"
      data-row={row.id}
      data-field="height"
      pattern={ref.magnitudeInputPattern || undefined}
      autocomplete="off"
      placeholder="e.g. 40mm or 1.5in"
      bind:value={row.height}
    />
    {@render copyPaste("height")}
  </td>

  <td
    class="bulk-td"
    data-col="links"
    data-col-type="links"
    style={hiddenStyle("links")}
  >
    <button
      type="button"
      class="links-toggle-btn w-full {linksOpen
        ? 'border-accent text-accent'
        : ''}"
      onclick={onToggleLinks}
    >
      Links (<span class="links-count" data-row={row.id}>{linksCount}</span>)
    </button>
  </td>

  <td
    class="bulk-td relative copyable-cell {clipboardType === 'description'
      ? 'has-clipboard'
      : ''}"
    data-col="description"
    data-col-type="description"
    style={hiddenStyle("description")}
  >
    <input
      type="text"
      class="bulk-input w-full"
      data-row={row.id}
      data-field="description"
      placeholder="—"
      bind:value={row.description}
    />
    {@render copyPaste("description")}
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
