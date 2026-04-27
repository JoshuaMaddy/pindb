"""Generic server-side data table with Alpine.js client-side search, sort, and pagination.

Usage:
    from pindb.templates.components.data_table import TableColumn, data_table

    row_tpl = tr(...)[...]  # htpy element with Alpine bindings; "row" refers to each item

    data_table(
        table_id="my_table",          # unique — scopes the Alpine component name
        columns=[
            TableColumn("Name", key="name"),
            TableColumn("Email", key="email"),
            TableColumn("Actions", sortable=False),
        ],
        rows=[{"id": 1, "name": "Josh", "email": "j@example.com"}, ...],
        row_template=row_tpl,
        search_keys=["name", "email"],
        page_size=25,
        default_sort_col="name",
        extra_state={"currentUserId": 7},  # merged into Alpine data as JSON values
    )

The component returns a Fragment containing a <script> (Alpine component registration)
and a <div x-data="..."> wrapping the table, search input, and pagination controls.

Row template notes:
- Alpine provides the variable `row` for each item in `paginatedRows`.
- Use dict-key kwargs for Alpine attributes: **{"x-text": "row.name", ":class": "..."}
- Do NOT put :key on the <tr>; it belongs on the wrapping <template x-for> (handled here).
"""

import json
from dataclasses import dataclass

from htpy import (
    Element,
    Fragment,
    VoidElement,
    button,
    div,
    fragment,
    input,
    script,
    span,
    table,
    tbody,
    th,
    thead,
    tr,
)
from htpy import template as html_template
from markupsafe import Markup


@dataclass
class TableColumn:
    label: str
    key: str | None = None  # sort key; None means column is not sortable
    sortable: bool = True


def data_table(
    table_id: str,
    columns: list[TableColumn],
    rows: list[dict],
    row_template: Element,
    search_keys: list[str],
    page_size: int = 25,
    default_sort_col: str | None = None,
    extra_state: dict | None = None,
) -> Fragment:
    """Return a search/sort/paginate table as an htpy Fragment."""
    component_name = f"dataTable_{table_id}"

    first_sortable_key: str | None = default_sort_col or next(
        (c.key for c in columns if c.sortable and c.key is not None), None
    )

    # Escape </script> sequences so embedded JSON cannot break the script tag.
    rows_json: str = json.dumps(rows).replace("</", "<\\/")
    search_keys_json: str = json.dumps(search_keys)
    default_sort_json: str = json.dumps(first_sortable_key)

    extra_lines = ""
    if extra_state:
        for k, v in extra_state.items():
            extra_lines += f"            {k}: {json.dumps(v)},\n"

    js = f"""
document.addEventListener('alpine:init', function () {{
    Alpine.data('{component_name}', function () {{
        return {{
            rows: {rows_json},
            search: '',
            sortCol: {default_sort_json},
            sortDir: 'asc',
            page: 1,
            pageSize: {page_size},
            searchKeys: {search_keys_json},
{extra_lines}
            get filteredRows() {{
                var r = this.rows;
                var q = this.search.trim().toLowerCase();
                if (q) {{
                    var keys = this.searchKeys;
                    r = r.filter(function (row) {{
                        return keys.some(function (k) {{
                            return String(row[k] || '').toLowerCase().indexOf(q) !== -1;
                        }});
                    }});
                }}
                var col = this.sortCol;
                if (col) {{
                    var dir = this.sortDir === 'asc' ? 1 : -1;
                    r = r.slice().sort(function (a, b) {{
                        return String(a[col] || '').localeCompare(String(b[col] || '')) * dir;
                    }});
                }}
                return r;
            }},

            get totalPages() {{
                return Math.max(1, Math.ceil(this.filteredRows.length / this.pageSize));
            }},

            get paginatedRows() {{
                var start = (this.page - 1) * this.pageSize;
                return this.filteredRows.slice(start, start + this.pageSize);
            }},

            sort: function (col) {{
                if (this.sortCol === col) {{
                    this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc';
                }} else {{
                    this.sortCol = col;
                    this.sortDir = 'asc';
                }}
                this.page = 1;
            }},

            setPage: function (p) {{
                this.page = Math.max(1, Math.min(p, this.totalPages));
            }},
        }};
    }});
}});
"""

    return fragment[
        script[Markup(js)],
        div(
            **{"x-data": component_name},
            class_="flex flex-col gap-2",
        )[
            _search_input(),
            div(class_="overflow-x-auto")[
                table(class_="w-full text-sm border-collapse")[
                    thead[
                        tr(class_="text-left border-b border-darker")[
                            [_th(col) for col in columns],
                        ]
                    ],
                    tbody[
                        html_template(
                            **{"x-for": "row in paginatedRows", ":key": "row.id"}
                        )[row_template],
                    ],
                ]
            ],
            _pagination_controls(total_row_count=len(rows)),
        ],
    ]


def _search_input() -> VoidElement:
    return input(
        type="search",
        placeholder="Search…",
        aria_label="Search",
        **{"x-model": "search", "@input": "page = 1"},
        class_="bg-lighter border border-lightest rounded px-2 py-1 text-base-text max-w-sm",
    )


def _th(col: TableColumn) -> Element:
    base_class = "py-2 pr-6 text-left whitespace-nowrap"
    if col.sortable and col.key is not None:
        return th(
            class_=f"{base_class} cursor-pointer select-none hover:text-accent",
            **{"@click": f"sort('{col.key}')"},
        )[
            col.label,
            span(
                **{
                    "x-show": f"sortCol === '{col.key}'",
                    "x-text": "sortDir === 'asc' ? ' ↑' : ' ↓'",
                }
            ),
        ]
    return th(class_=base_class)[col.label]


def _pagination_controls(total_row_count: int) -> Element:
    return div(class_="flex items-center gap-2 text-sm")[
        button(
            class_="btn btn-sm",
            aria_label="Previous page",
            **{"@click": "setPage(page - 1)", ":disabled": "page <= 1"},
        )["←"],
        span[
            "Page ",
            span(**{"x-text": "page"}),
            " of ",
            span(**{"x-text": "totalPages"}),
        ],
        button(
            class_="btn btn-sm",
            aria_label="Next page",
            **{"@click": "setPage(page + 1)", ":disabled": "page >= totalPages"},
        )["→"],
        span(class_="ml-auto text-lighter-hover")[
            span(**{"x-text": "filteredRows.length"}),
            f" of {total_row_count}",
        ],
    ]
