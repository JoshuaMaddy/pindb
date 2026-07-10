// Bulk tag grid row model + (de)serialization matching
// routes/bulk/tag.py::BulkTagRow.

export type TagRowData = {
  id: string;
  clientId: string;
  name: string;
  category: string;
  implications: string[];
  aliases: string[];
  description: string;
  error: string | null;
};

let rowCounter = 0;

function clientId(): string {
  return `${Math.random().toString(36).slice(2, 10)}-${Date.now().toString(36)}`;
}

export function newTagRow(): TagRowData {
  rowCounter += 1;
  return {
    id: `row-${rowCounter}`,
    clientId: clientId(),
    name: "",
    category: "general",
    implications: [],
    aliases: [],
    description: "",
    error: null,
  };
}

export function normalizeTagName(name: string): string {
  return name.trim().toLowerCase().replace(/\s+/g, "_");
}

export function toPayload(row: TagRowData): Record<string, unknown> {
  return {
    client_id: row.clientId,
    name: normalizeTagName(row.name),
    category: row.category || "general",
    description: row.description || null,
    aliases: [...row.aliases],
    implication_names: [...row.implications],
  };
}
