// Bulk import grid state — the single source of truth that replaces the three
// legacy layers (per-row Tom Select maps, live Alpine sub-rows, tr.dataset
// serialization). Submit payload / sessionStorage draft shapes reproduce the
// legacy contract exactly (see routes/bulk/pin.py::PinRowInput).

export type Option = { value: string; text: string; category?: string };
export type GradeEntry = { name: string; price: string };

export type EntityType = "shop" | "tag" | "artist" | "pin_set";

export type BulkRowData = {
  id: string;
  name: string;
  acquisitionType: string;
  frontImageGuid: string | null;
  backImageGuid: string | null;
  currencyId: string;
  // Selected options per multi field (value strings + display metadata —
  // metadata rides the draft/duplicate shape as *_options).
  shops: Option[];
  tags: Option[];
  artists: Option[];
  pinSets: Option[];
  grades: GradeEntry[];
  links: string[];
  limitedEdition: "" | "true" | "false";
  numberProduced: string;
  releaseDate: string;
  endDate: string;
  fundingType: string;
  posts: string;
  width: string;
  height: string;
  description: string;
  error: string | null;
};

let rowCounter = 0;

export function newRow(defaultCurrencyId: number): BulkRowData {
  rowCounter += 1;
  return {
    id: `row-${rowCounter}`,
    name: "",
    acquisitionType: "",
    frontImageGuid: null,
    backImageGuid: null,
    currencyId: String(defaultCurrencyId),
    shops: [],
    tags: [],
    artists: [],
    pinSets: [],
    grades: [{ name: "Normal", price: "" }],
    links: [""],
    limitedEdition: "",
    numberProduced: "",
    releaseDate: "",
    endDate: "",
    fundingType: "",
    posts: "1",
    width: "",
    height: "",
    description: "",
    error: null,
  };
}

// --- legacy-shape (de)serialization -----------------------------------------

/** Legacy collectRowData shape: submit payload + sessionStorage draft. */
export function toLegacyShape(row: BulkRowData): Record<string, unknown> {
  return {
    name: row.name,
    acquisition_type: row.acquisitionType,
    front_image_guid: row.frontImageGuid,
    back_image_guid: row.backImageGuid,
    currency_id: parseInt(row.currencyId, 10),
    shop_names: row.shops.map((option) => option.value),
    tag_names: row.tags.map((option) => option.value),
    artist_names: row.artists.map((option) => option.value),
    pin_set_names: row.pinSets.map((option) => option.value),
    shop_options: row.shops.map((option) => ({ ...option })),
    tag_options: row.tags.map((option) => ({ ...option })),
    artist_options: row.artists.map((option) => ({ ...option })),
    pin_set_options: row.pinSets.map((option) => ({ ...option })),
    grades: row.grades
      .filter((grade) => grade.name)
      .map((grade) => ({
        name: grade.name,
        price: grade.price === "" ? null : parseFloat(grade.price),
      })),
    links: row.links.map((link) => link.trim()).filter(Boolean),
    limited_edition:
      row.limitedEdition === "true"
        ? true
        : row.limitedEdition === "false"
          ? false
          : null,
    number_produced: row.numberProduced
      ? parseInt(row.numberProduced, 10)
      : null,
    release_date: row.releaseDate || null,
    end_date: row.endDate || null,
    funding_type: row.fundingType || null,
    posts: parseInt(row.posts || "1", 10),
    width: row.width || null,
    height: row.height || null,
    description: row.description || null,
  };
}

function readOptions(
  raw: Record<string, unknown>,
  optionsKey: string,
  namesKey: string,
): Option[] {
  const options = raw[optionsKey];
  if (Array.isArray(options) && options.length) {
    return options.map((option) => ({
      value: String(option.value),
      text: String(option.text ?? option.value),
      ...(option.category ? { category: String(option.category) } : {}),
    }));
  }
  const names = raw[namesKey];
  if (Array.isArray(names)) {
    return names.map((name) => ({ value: String(name), text: String(name) }));
  }
  return [];
}

/** Inverse of toLegacyShape — consumes drafts and duplicate-row prefills. */
export function fromLegacyShape(
  raw: Record<string, unknown>,
  defaultCurrencyId: number,
): BulkRowData {
  const row = newRow(defaultCurrencyId);
  row.name = String(raw.name ?? "");
  row.acquisitionType = String(raw.acquisition_type ?? "");
  row.frontImageGuid = raw.front_image_guid ? String(raw.front_image_guid) : null;
  row.backImageGuid = raw.back_image_guid ? String(raw.back_image_guid) : null;
  if (raw.currency_id != null) row.currencyId = String(raw.currency_id);
  row.shops = readOptions(raw, "shop_options", "shop_names");
  row.tags = readOptions(raw, "tag_options", "tag_names");
  row.artists = readOptions(raw, "artist_options", "artist_names");
  row.pinSets = readOptions(raw, "pin_set_options", "pin_set_names");
  if (Array.isArray(raw.grades) && raw.grades.length) {
    row.grades = raw.grades.map((grade: { name?: unknown; price?: unknown }) => ({
      name: String(grade.name ?? ""),
      price: grade.price == null ? "" : String(grade.price),
    }));
  }
  if (Array.isArray(raw.links) && raw.links.length) {
    row.links = raw.links.map(String);
  }
  row.limitedEdition =
    raw.limited_edition === true
      ? "true"
      : raw.limited_edition === false
        ? "false"
        : "";
  row.numberProduced = raw.number_produced == null ? "" : String(raw.number_produced);
  row.releaseDate = raw.release_date ? String(raw.release_date) : "";
  row.endDate = raw.end_date ? String(raw.end_date) : "";
  row.fundingType = raw.funding_type ? String(raw.funding_type) : "";
  row.posts = raw.posts == null ? "1" : String(raw.posts);
  row.width = raw.width ? String(raw.width) : "";
  row.height = raw.height ? String(raw.height) : "";
  row.description = raw.description ? String(raw.description) : "";
  return row;
}

export function validateRow(row: BulkRowData): string | null {
  const errors: string[] = [];
  if (!row.name.trim()) errors.push("Name is required");
  if (!row.frontImageGuid) errors.push("Front image is required");
  if (!row.acquisitionType) errors.push("Acquisition type is required");
  if (!row.grades.some((grade) => grade.name)) {
    errors.push("At least one grade is required");
  }
  return errors.length ? errors.join("; ") : null;
}
