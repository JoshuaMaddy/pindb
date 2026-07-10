<script lang="ts">
  // Manage Users table: client-side search / sort / pagination over the
  // server-provided user rows, plus role-management action forms.
  // Successor of the generic Alpine data_table (this was its only consumer).

  type UserRow = {
    id: number;
    username: string;
    email: string;
    is_admin: boolean;
    is_editor: boolean;
    promote_url: string;
    demote_url: string;
    promote_editor_url: string;
    demote_editor_url: string;
    delete_account_url: string;
  };

  let {
    rows,
    currentUserId,
    pageSize = 25,
  }: {
    rows: UserRow[];
    currentUserId: number;
    pageSize?: number;
  } = $props();

  let search = $state("");
  let sortCol = $state<"username" | "email" | "is_admin">("username");
  let sortDir = $state<"asc" | "desc">("asc");
  let page = $state(1);

  const filteredRows = $derived.by(() => {
    let result = rows;
    const query = search.trim().toLowerCase();
    if (query) {
      result = result.filter(
        (row) =>
          row.username.toLowerCase().includes(query) ||
          row.email.toLowerCase().includes(query),
      );
    }
    const direction = sortDir === "asc" ? 1 : -1;
    const column = sortCol;
    return [...result].sort(
      (a, b) =>
        String(a[column] || "").localeCompare(String(b[column] || "")) *
        direction,
    );
  });
  const totalPages = $derived(
    Math.max(1, Math.ceil(filteredRows.length / pageSize)),
  );
  const paginatedRows = $derived(
    filteredRows.slice((page - 1) * pageSize, page * pageSize),
  );

  function sort(column: "username" | "email" | "is_admin"): void {
    if (sortCol === column) {
      sortDir = sortDir === "asc" ? "desc" : "asc";
    } else {
      sortCol = column;
      sortDir = "asc";
    }
    page = 1;
  }

  function setPage(next: number): void {
    page = Math.max(1, Math.min(next, totalPages));
  }

  const deleteConfirmMessage = (username: string): string =>
    `Permanently erase account '${username}'?\n\n` +
    "This anonymises all audit-log references, drops sessions, " +
    "OAuth links, favorites, owned and wanted pins, and deletes " +
    "their personal pin sets. Cannot be undone.";

  const SORTABLE: { label: string; key: "username" | "email" | "is_admin" }[] =
    [
      { label: "Username", key: "username" },
      { label: "Email", key: "email" },
      { label: "Role", key: "is_admin" },
    ];
</script>

<div class="flex flex-col gap-2">
  <input
    type="search"
    placeholder="Search…"
    aria-label="Search"
    class="bg-lighter border border-lightest rounded px-2 py-1 text-base-text max-w-sm"
    bind:value={search}
    oninput={() => (page = 1)}
  />
  <div class="overflow-x-auto">
    <table class="w-full text-sm border-collapse">
      <thead>
        <tr class="text-left border-b border-darker">
          {#each SORTABLE as column (column.key)}
            <th
              class="py-2 pr-6 text-left whitespace-nowrap cursor-pointer select-none hover:text-accent"
              onclick={() => sort(column.key)}
            >
              {column.label}
              {#if sortCol === column.key}
                <span>{sortDir === "asc" ? " ↑" : " ↓"}</span>
              {/if}
            </th>
          {/each}
          <th class="py-2 pr-6 text-left whitespace-nowrap">Actions</th>
        </tr>
      </thead>
      <tbody>
        {#each paginatedRows as row (row.id)}
          {@const isSelfAdmin = row.is_admin && row.id === currentUserId}
          <tr class="border-b border-darker">
            <td class="py-2 pr-6">{row.username}</td>
            <td class="py-2 pr-6 text-lighter-hover">{row.email || "—"}</td>
            <td class="py-2 pr-6">
              <div class="flex gap-1 flex-wrap">
                <span
                  class="text-xs font-semibold px-2 py-0.5 rounded {row.is_admin
                    ? 'bg-error-dark-hover text-error-main-hover'
                    : 'bg-darker text-lightest-hover'}"
                >
                  {row.is_admin ? "Admin" : "User"}
                </span>
                {#if row.is_editor && !row.is_admin}
                  <span
                    class="text-xs font-semibold px-2 py-0.5 rounded bg-blue-700 text-blue-100"
                  >
                    Editor
                  </span>
                {/if}
              </div>
            </td>
            <td class="py-2">
              <div class="flex gap-2 flex-wrap">
                <form
                  method="post"
                  action={row.is_admin ? row.demote_url : row.promote_url}
                >
                  <button
                    type="submit"
                    class={isSelfAdmin
                      ? "btn btn-sm opacity-50 cursor-not-allowed"
                      : row.is_admin
                        ? "btn btn-sm btn-error"
                        : "btn btn-sm btn-primary"}
                    disabled={isSelfAdmin}
                  >
                    {isSelfAdmin
                      ? "Cannot demote self"
                      : row.is_admin
                        ? "Demote Admin"
                        : "Promote to Admin"}
                  </button>
                </form>
                {#if !row.is_admin}
                  <form
                    method="post"
                    action={row.is_editor
                      ? row.demote_editor_url
                      : row.promote_editor_url}
                  >
                    <button
                      type="submit"
                      class={row.is_editor
                        ? "btn btn-sm btn-warning"
                        : "btn btn-sm btn-secondary"}
                    >
                      {row.is_editor ? "Revoke Editor" : "Promote to Editor"}
                    </button>
                  </form>
                {/if}
                {#if row.id !== currentUserId}
                  <form
                    method="post"
                    action={row.delete_account_url}
                    onsubmit={(evt) => {
                      if (!confirm(deleteConfirmMessage(row.username))) {
                        evt.preventDefault();
                      }
                    }}
                  >
                    <button type="submit" class="btn btn-sm btn-error">
                      Erase account
                    </button>
                  </form>
                {/if}
              </div>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
  <div class="flex items-center gap-2 text-sm">
    <button
      class="btn btn-sm"
      aria-label="Previous page"
      disabled={page <= 1}
      onclick={() => setPage(page - 1)}
    >
      ←
    </button>
    <span>Page <span>{page}</span> of <span>{totalPages}</span></span>
    <button
      class="btn btn-sm"
      aria-label="Next page"
      disabled={page >= totalPages}
      onclick={() => setPage(page + 1)}
    >
      →
    </button>
    <span class="ml-auto text-lighter-hover">
      <span>{filteredRows.length}</span>
      of {rows.length}
    </span>
  </div>
</div>
