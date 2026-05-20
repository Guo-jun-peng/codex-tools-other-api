import type { ReactNode } from 'react'

interface Column<T> {
  key: string
  header: string
  render?: (row: T) => ReactNode
}

interface Props<T> {
  columns: Column<T>[]
  rows: T[]
  emptyState?: ReactNode
  rowKey: (row: T) => string
}

export default function DataTable<T>({ columns, rows, emptyState, rowKey }: Props<T>) {
  return (
    <div className="table-container">
      <table>
        <thead>
          <tr>{columns.map((col) => <th key={col.key}>{col.header}</th>)}</tr>
        </thead>
        <tbody>
          {rows.length === 0 && emptyState ? (
            <tr><td colSpan={columns.length}>{emptyState}</td></tr>
          ) : (
            rows.map((row) => (
              <tr key={rowKey(row)}>
                {columns.map((col) => (
                  <td key={col.key}>{col.render ? col.render(row) : (row as any)[col.key]}</td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
