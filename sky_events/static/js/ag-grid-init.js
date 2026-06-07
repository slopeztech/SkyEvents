(function () {
  "use strict";

  function toCellValue(cell) {
    if (!cell) {
      return "";
    }

    return (cell.innerHTML || cell.textContent || "").replace(/\s+/g, " ").trim();
  }

  function convertTable(table) {
    if (!table || table.dataset.agGridInitialized === "true") {
      return;
    }

    if (!window.agGrid || !window.agGrid.Grid) {
      return;
    }

    var headers = Array.prototype.slice.call(table.querySelectorAll("thead th"));
    if (!headers.length) {
      return;
    }

    var columnDefs = headers.map(function (th, index) {
      return {
        headerName: (th.textContent || "").replace(/\s+/g, " ").trim() || "Column " + (index + 1),
        field: "col_" + index,
        sortable: true,
        filter: true,
        resizable: true,
        flex: 1,
        minWidth: 140,
        cellDataType: "text",
        valueFormatter: function (params) {
          return params.value || "";
        },
        cellRenderer: function (params) {
          return params.value || "";
        },
      };
    });

    var rowData = Array.prototype.slice.call(table.querySelectorAll("tbody tr")).map(function (row) {
      var cells = Array.prototype.slice.call(row.querySelectorAll("td"));
      var record = {};

      headers.forEach(function (th, index) {
        record["col_" + index] = toCellValue(cells[index]);
      });

      return record;
    });

    var shell = document.createElement("div");
    shell.className = "ag-grid-shell rounded-2xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 shadow-sm overflow-hidden";

    var gridDiv = document.createElement("div");
    gridDiv.className = "ag-theme-alpine-dark";
    gridDiv.style.width = "100%";
    gridDiv.style.height = Math.max(340, rowData.length * 56 + 110) + "px";

    shell.appendChild(gridDiv);
    table.parentNode.insertBefore(shell, table);
    table.style.display = "none";

    var gridApi = window.agGrid.createGrid(gridDiv, {
      rowData: rowData,
      columnDefs: columnDefs,
      defaultColDef: {
        sortable: true,
        filter: true,
        resizable: true,
        flex: 1,
        minWidth: 140,
      },
      animateRows: true,
      pagination: true,
      paginationPageSize: 12,
      paginationPageSizeSelector: [10, 12, 25, 50],
      domLayout: "normal",
      suppressColumnVirtualisation: true,
      onFirstDataRendered: function (params) {
        if (gridDiv.getBoundingClientRect().width > 0) {
          params.api.sizeColumnsToFit();
        } else {
          window.setTimeout(function () {
            if (gridDiv.getBoundingClientRect().width > 0) {
              params.api.sizeColumnsToFit();
            }
          }, 150);
        }
      },
    });

    gridDiv.__agGridApi = gridApi;

    table.dataset.agGridInitialized = "true";
  }

  function initTables() {
    if (!window.agGrid || typeof window.agGrid.createGrid !== "function") {
      return;
    }

    Array.prototype.slice.call(document.querySelectorAll("table.data-table, table.ag-grid-table")).forEach(convertTable);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      window.setTimeout(initTables, 0);
    });
  } else {
    window.setTimeout(initTables, 0);
  }
})();
