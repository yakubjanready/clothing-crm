import { EmptyState } from "./EmptyState";

export interface Column<T> {
  key: keyof T | string;
  header: string;
  render?: (row: T) => React.ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  emptyTitle?: string;
}

export function DataTable<T>({ columns, rows, rowKey, emptyTitle }: DataTableProps<T>) {
  if (rows.length === 0) {
    return <EmptyState title={emptyTitle} />;
  }
  return (
    <div className="overflow-x-auto rounded-lg border bg-card">
      <table className="w-full text-sm">
        <thead className="border-b bg-muted/40">
          <tr>
            {columns.map((c) => (
              <th
                key={String(c.key)}
                className={`px-4 py-3 text-left font-medium text-muted-foreground ${c.className ?? ""}`}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)} className="border-b last:border-0 hover:bg-muted/30">
              {columns.map((c) => (
                <td key={String(c.key)} className={`px-4 py-3 ${c.className ?? ""}`}>
                  {c.render
                    ? c.render(row)
                    : String((row as Record<string, unknown>)[c.key as string] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
