<script lang="ts">
  import ClipboardPaste from "@lucide/svelte/icons/clipboard-paste";
  import LoaderCircle from "@lucide/svelte/icons/loader-circle";
  import Plus from "@lucide/svelte/icons/plus";
  import Upload from "@lucide/svelte/icons/upload";

  import type { Option } from "../../lib/MultiSelect.svelte";
  import BulkRow from "./BulkRow.svelte";
  import ColumnsMenu from "./ColumnsMenu.svelte";
  import GradesSubRow from "./GradesSubRow.svelte";
  import LinksSubRow from "./LinksSubRow.svelte";
  import SuccessModal, { type SubmitResult } from "./SuccessModal.svelte";
  import {
    fromLegacyShape,
    newRow,
    toLegacyShape,
    validateRow,
    type BulkRowData,
    type EntityType,
  } from "./state.svelte";

  type Ref = {
    uploadImageUrl: string;
    submitUrl: string;
    optionsBaseUrl: string;
    nameCheckUrl: string;
    currencies: { value: number | string; text: string }[];
    acquisitionTypes: Option[];
    fundingTypes: Option[];
    defaultCurrencyId: number;
    magnitudeInputPattern: string;
    optionalCols: { key: string; label: string }[];
  };

  let props: Ref = $props();

  // Island props are static per mount — initial-value capture is intended.
  // svelte-ignore state_referenced_locally
  const ref = {
    uploadImageUrl: props.uploadImageUrl,
    optionsBaseUrl: props.optionsBaseUrl,
    nameCheckUrl: props.nameCheckUrl,
    currencies: props.currencies.map((currency) => ({
      value: String(currency.value),
      text: currency.text,
    })),
    acquisitionTypes: props.acquisitionTypes,
    fundingTypes: props.fundingTypes,
    magnitudeInputPattern: props.magnitudeInputPattern,
  };

  const DRAFT_KEY = "bulk_persist";

  function restoreDraft(): BulkRowData[] | null {
    const navEntry = performance.getEntriesByType(
      "navigation",
    )[0] as PerformanceNavigationTiming | undefined;
    if (navEntry?.type !== "reload") {
      sessionStorage.removeItem(DRAFT_KEY);
      return null;
    }
    const raw = sessionStorage.getItem(DRAFT_KEY);
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed) || !parsed.length) return null;
      return parsed.map((entry) =>
        fromLegacyShape(entry, props.defaultCurrencyId),
      );
    } catch {
      return null;
    }
  }

  // Island props are static per mount — initial-value capture is intended.
  // svelte-ignore state_referenced_locally
  let rows = $state<BulkRowData[]>(
    restoreDraft() ?? [newRow(props.defaultCurrencyId)],
  );
  let localOptions = $state<Record<EntityType, Option[]>>({
    shop: [],
    tag: [],
    artist: [],
    pin_set: [],
  });
  let clipboard = $state<{ type: string; values: unknown } | null>(null);
  let openGradesRowId = $state<string | null>(null);
  let openLinksRowId = $state<string | null>(null);
  let submitting = $state(false);
  let submitResult = $state<SubmitResult | null>(null);
  let selectAll = $state(false);

  function loadSavedCols(): Record<string, boolean> {
    try {
      return JSON.parse(localStorage.getItem("bulk_visible_cols") ?? "{}");
    } catch {
      return {};
    }
  }
  const savedCols = loadSavedCols();
  // Island props are static per mount — initial-value capture is intended.
  // svelte-ignore state_referenced_locally
  let visibleCols = $state<Record<string, boolean>>(
    Object.fromEntries(
      props.optionalCols.map((col) => [col.key, savedCols[col.key] ?? true]),
    ),
  );

  // Draft persistence — one debounced effect replaces the legacy
  // document-level input/change listeners.
  let draftTimer: ReturnType<typeof setTimeout> | undefined;
  $effect(() => {
    const serialized = JSON.stringify(rows.map(toLegacyShape));
    clearTimeout(draftTimer);
    draftTimer = setTimeout(() => {
      sessionStorage.setItem(DRAFT_KEY, serialized);
    }, 300);
  });

  const nameMinWidth = $derived.by(() => {
    const maxChars = Math.max(
      15,
      ...rows.map((row) => row.name.length),
    );
    return `${maxChars + 2}ch`;
  });

  function registerLocalOption(entityType: EntityType, option: Option): void {
    if (
      !localOptions[entityType].some((known) => known.value === option.value)
    ) {
      localOptions[entityType].push(option);
    }
  }

  function addRow(): void {
    rows.push(newRow(props.defaultCurrencyId));
  }

  function duplicateRow(index: number): void {
    const copy = fromLegacyShape(
      toLegacyShape(rows[index]),
      props.defaultCurrencyId,
    );
    copy.frontImageGuid = null;
    copy.backImageGuid = null;
    rows.push(copy);
  }

  function deleteRow(index: number): void {
    const row = rows[index];
    if (openGradesRowId === row.id) openGradesRowId = null;
    if (openLinksRowId === row.id) openLinksRowId = null;
    rows.splice(index, 1);
  }

  // --- copy/paste columns ---------------------------------------------------

  const MULTI_FIELDS: Record<string, "shops" | "tags" | "artists" | "pinSets"> =
    {
      shops: "shops",
      tags: "tags",
      artists: "artists",
      pin_sets: "pinSets",
    };
  const SCALAR_FIELDS: Record<string, keyof BulkRowData> = {
    name: "name",
    acquisition_type: "acquisitionType",
    currency_id: "currencyId",
    funding_type: "fundingType",
    number_produced: "numberProduced",
    release_date: "releaseDate",
    end_date: "endDate",
    posts: "posts",
    width: "width",
    height: "height",
    description: "description",
  };

  function copyColumn(index: number, colType: string): void {
    const row = rows[index];
    let values: unknown;
    if (colType === "grades") {
      values = row.grades.map((grade) => ({ ...grade }));
    } else if (colType in MULTI_FIELDS) {
      values = row[MULTI_FIELDS[colType]].map((option) => ({ ...option }));
    } else {
      values = row[SCALAR_FIELDS[colType]];
    }
    clipboard = { type: colType, values };
  }

  function pasteInto(row: BulkRowData, colType: string): void {
    if (!clipboard || clipboard.type !== colType) return;
    const values = clipboard.values;
    if (colType === "grades") {
      row.grades = (values as { name: string; price: string }[]).map(
        (grade) => ({ ...grade }),
      );
    } else if (colType in MULTI_FIELDS) {
      const options = (values as Option[]).map((option) => ({ ...option }));
      const entityType = (
        colType === "pin_sets" ? "pin_set" : colType.slice(0, -1)
      ) as EntityType;
      options.forEach((option) => registerLocalOption(entityType, option));
      row[MULTI_FIELDS[colType]] = options;
    } else {
      (row as unknown as Record<string, unknown>)[SCALAR_FIELDS[colType]] =
        values;
    }
  }

  function pasteColumnToAll(colType: string): void {
    rows.forEach((row) => pasteInto(row, colType));
  }

  // --- submit -----------------------------------------------------------

  async function submitAll(): Promise<void> {
    openGradesRowId = null;
    openLinksRowId = null;

    let allValid = true;
    for (const row of rows) {
      row.error = validateRow(row);
      if (row.error) allValid = false;
    }
    if (!allValid || !rows.length) return;

    submitting = true;
    try {
      const response = await fetch(props.submitUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pins: rows.map(toLegacyShape) }),
      });
      if (!response.ok) {
        throw new Error(`Server error ${response.status}`);
      }
      const result: SubmitResult = await response.json();
      for (const entry of result.results) {
        if (!entry.success) {
          rows[entry.index].error = entry.error || "Unknown error";
        }
      }
      const failedIds = new Set(
        result.results
          .filter((entry) => !entry.success)
          .map((entry) => rows[entry.index].id),
      );
      rows = rows.filter((row) => failedIds.has(row.id));
      submitResult = result;
    } catch (error) {
      alert(String(error));
    } finally {
      submitting = false;
    }
  }

  const REQUIRED_HEADERS: {
    colType: string;
    label: string;
    className: string;
  }[] = [
    { colType: "name", label: "Name *", className: "bulk-th bulk-sticky-left bulk-sticky-col-2 min-w-[15ch]" },
    { colType: "shops", label: "Shops *", className: "bulk-th min-w-45" },
    { colType: "acquisition_type", label: "Acquisition *", className: "bulk-th min-w-35" },
    { colType: "grades", label: "Grades *", className: "bulk-th min-w-25" },
    { colType: "currency_id", label: "Currency *", className: "bulk-th min-w-30" },
    { colType: "tags", label: "Tags *", className: "bulk-th min-w-[320px]" },
  ];

  const OPTIONAL_HEADERS: {
    key: string;
    colType: string | null;
    label: string;
    className: string;
  }[] = [
    { key: "artists", colType: "artists", label: "Artists", className: "bulk-th min-w-40" },
    { key: "pin_sets", colType: "pin_sets", label: "Pin Sets", className: "bulk-th min-w-40" },
    { key: "limited_edition", colType: null, label: "Ltd. Ed.", className: "bulk-th min-w-20" },
    { key: "number_produced", colType: "number_produced", label: "# Produced", className: "bulk-th min-w-25" },
    { key: "release_date", colType: "release_date", label: "Release Date", className: "bulk-th min-w-32.5" },
    { key: "end_date", colType: "end_date", label: "End Date", className: "bulk-th min-w-32.5" },
    { key: "funding_type", colType: "funding_type", label: "Funding", className: "bulk-th min-w-32.5" },
    { key: "posts", colType: "posts", label: "Posts", className: "bulk-th min-w-17.5" },
    { key: "width", colType: "width", label: "Width", className: "bulk-th min-w-22.5" },
    { key: "height", colType: "height", label: "Height", className: "bulk-th min-w-22.5" },
    { key: "links", colType: null, label: "Links", className: "bulk-th min-w-25" },
    { key: "description", colType: "description", label: "Description", className: "bulk-th min-w-45" },
  ];

  const colspan = $derived(9 + props.optionalCols.length + 1);
</script>

<div class="flex items-center gap-2 flex-wrap">
  <h1 class="grow">Bulk Import Pins</h1>
  <ColumnsMenu cols={props.optionalCols} bind:visible={visibleCols} />
  <button
    id="add-row-btn"
    type="button"
    class="flex items-center gap-1"
    onclick={addRow}
  >
    <Plus aria-hidden="true" /> Add Row
  </button>
  <button
    id="submit-btn"
    type="button"
    class="flex items-center gap-1 border-accent text-accent"
    disabled={submitting}
    onclick={() => void submitAll()}
  >
    {#if submitting}
      <LoaderCircle class="animate-spin" aria-hidden="true" />
    {:else}
      <Upload aria-hidden="true" />
    {/if}
    <span id="submit-label">Submit ({rows.length})</span>
  </button>
</div>
<hr />
<div
  class="overflow-x-auto overflow-y-clip rounded-lg border border-lightest [container-type:inline-size]"
>
  <table class="bulk-table w-full border-collapse text-sm">
    <thead>
      <tr class="border-b border-lightest">
        <th class="bulk-th bulk-sticky-left bulk-sticky-col-0 w-8">
          <input
            type="checkbox"
            id="select-all-rows"
            aria-label="Select all rows"
            bind:checked={selectAll}
            onchange={() => {
              document
                .querySelectorAll<HTMLInputElement>(".row-checkbox")
                .forEach((checkbox) => {
                  checkbox.checked = selectAll;
                });
            }}
          />
        </th>
        <th class="bulk-th bulk-sticky-left bulk-sticky-col-1 w-22">Front *</th>
        <th class="bulk-th w-22">Back</th>
        {#each REQUIRED_HEADERS as header (header.colType)}
          <th
            class="{header.className} relative"
            data-col-type={header.colType}
            style={header.colType === "name"
              ? `min-width: ${nameMinWidth};`
              : ""}
          >
            {header.label}
            {#if clipboard && clipboard.type === header.colType}
              <button
                type="button"
                class="header-paste-btn"
                title="Paste to all rows"
                onclick={() => pasteColumnToAll(header.colType)}
              >
                <ClipboardPaste />
              </button>
            {/if}
          </th>
        {/each}
        {#each OPTIONAL_HEADERS as header (header.key)}
          <th
            class="{header.className} relative"
            data-col={header.key}
            data-col-type={header.colType}
            style={visibleCols[header.key] === false ? "display: none;" : ""}
          >
            {header.label}
            {#if header.colType && clipboard && clipboard.type === header.colType}
              <button
                type="button"
                class="header-paste-btn"
                title="Paste to all rows"
                onclick={() => header.colType && pasteColumnToAll(header.colType)}
              >
                <ClipboardPaste />
              </button>
            {/if}
          </th>
        {/each}
        <th class="bulk-th w-20">Actions</th>
      </tr>
    </thead>
    <tbody id="bulk-tbody">
      {#each rows as row, index (row.id)}
        <BulkRow
          bind:row={rows[index]}
          {ref}
          {localOptions}
          visible={visibleCols}
          clipboardType={clipboard?.type ?? null}
          {nameMinWidth}
          gradesOpen={openGradesRowId === row.id}
          linksOpen={openLinksRowId === row.id}
          onToggleGrades={() => {
            openGradesRowId = openGradesRowId === row.id ? null : row.id;
          }}
          onToggleLinks={() => {
            openLinksRowId = openLinksRowId === row.id ? null : row.id;
          }}
          onDuplicate={() => duplicateRow(index)}
          onDelete={() => deleteRow(index)}
          onCopy={(colType) => copyColumn(index, colType)}
          onPaste={(colType) => pasteInto(rows[index], colType)}
          onOptionCreate={registerLocalOption}
        />
        {#if openGradesRowId === row.id}
          <GradesSubRow bind:grades={rows[index].grades} {colspan} />
        {/if}
        {#if openLinksRowId === row.id}
          <LinksSubRow bind:links={rows[index].links} {colspan} />
        {/if}
      {/each}
    </tbody>
  </table>
</div>
{#if submitResult}
  <SuccessModal result={submitResult} onClose={() => (submitResult = null)} />
{/if}
