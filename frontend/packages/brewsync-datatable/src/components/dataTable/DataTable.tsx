import {type Table as ReactTable, type RowData} from "@tanstack/react-table";
import {DataTableContextProvider, Table} from "@/components";

export type DataTableProps<TData extends RowData> = {
    table: ReactTable<TData>;
}

export default function DataTable<TData extends RowData>({
    table,
}: DataTableProps<TData>) {
    return (
        <DataTableContextProvider value={{
            meta: table.options.meta || {},
        }}>
            <Table table={table} />
        </DataTableContextProvider>
    )
}
