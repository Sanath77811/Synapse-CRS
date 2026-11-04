import type { ReactNode } from "react";

export type Column<T> = {
  key: string;
  header: string;
  width?: string;
  mono?: boolean;
  render: (row: T) => ReactNode;
};

export function DataTable<T extends { id: string }>({
  columns,
  rows,
  onSelect,
  selectedId,
  empty,
}: {
  columns: Column<T>[];
  rows: T[];
  onSelect?: (row: T) => void;
  selectedId?: string;
  empty: string;
}) {
  if (rows.length === 0) {
    return <p className="muted">{empty}</p>;
  }
  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key} style={column.width ? { width: column.width } : undefined}>
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.id}
              className={selectedId === row.id ? "is-selected" : undefined}
              onClick={onSelect ? () => onSelect(row) : undefined}
              tabIndex={onSelect ? 0 : undefined}
              onKeyDown={
                onSelect
                  ? (event) => {
                      if (event.key === "Enter") {
                        onSelect(row);
                      }
                    }
                  : undefined
              }
            >
              {columns.map((column) => (
                <td key={column.key} className={column.mono ? "mono" : undefined}>
                  {column.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
