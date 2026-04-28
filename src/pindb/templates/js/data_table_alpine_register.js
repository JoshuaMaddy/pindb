document.addEventListener("alpine:init", function () {
  document
    .querySelectorAll("script[type='application/json'].pindb-data-table-spec")
    .forEach(function (el) {
      var spec;
      try {
        spec = JSON.parse(el.textContent);
      } catch {
        return;
      }
      if (!spec || !spec.componentName) return;
      Alpine.data(spec.componentName, function () {
        var extra = spec.extraState || {};
        return Object.assign(
          {
            rows: spec.rows,
            search: "",
            sortCol: spec.defaultSortCol,
            sortDir: "asc",
            page: 1,
            pageSize: spec.pageSize,
            searchKeys: spec.searchKeys,
            get filteredRows() {
              var r = this.rows;
              var q = this.search.trim().toLowerCase();
              if (q) {
                var keys = this.searchKeys;
                r = r.filter(function (row) {
                  return keys.some(function (k) {
                    return (
                      String(row[k] || "")
                        .toLowerCase()
                        .indexOf(q) !== -1
                    );
                  });
                });
              }
              var col = this.sortCol;
              if (col) {
                var dir = this.sortDir === "asc" ? 1 : -1;
                r = r.slice().sort(function (a, b) {
                  return (
                    String(a[col] || "").localeCompare(String(b[col] || "")) *
                    dir
                  );
                });
              }
              return r;
            },
            get totalPages() {
              return Math.max(
                1,
                Math.ceil(this.filteredRows.length / this.pageSize),
              );
            },
            get paginatedRows() {
              var start = (this.page - 1) * this.pageSize;
              return this.filteredRows.slice(start, start + this.pageSize);
            },
            sort: function (col) {
              if (this.sortCol === col) {
                this.sortDir = this.sortDir === "asc" ? "desc" : "asc";
              } else {
                this.sortCol = col;
                this.sortDir = "asc";
              }
              this.page = 1;
            },
            setPage: function (p) {
              this.page = Math.max(1, Math.min(p, this.totalPages));
            },
          },
          extra,
        );
      });
    });
});
