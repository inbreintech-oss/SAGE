import {Text} from "@mantine/core";
import {RowData, Table} from "@tanstack/react-table";

export type RowCounterProps<TData extends RowData> = {
    table: Table<TData>
}

export default function RowCounter<TData extends RowData>({
    table
}: RowCounterProps<TData>) {
    const renderCounterText = (table: Table<TData>) => {
        const rows = table.getRowModel().rows;
        const coreRows = table.getCoreRowModel().rows;

        if (table.options.meta?.enablePagination === true) {
            const paging = table.getState().pagination;

            const from = paging.pageIndex * paging.pageSize + 1;
            const to = Math.min((paging.pageIndex + 1) * paging.pageSize, coreRows.length);

            return rows.length === 0 ?
                0 :
                `${from.toLocaleString()}-${to.toLocaleString()} of ${coreRows.length.toLocaleString()}`;
        } else {
            return coreRows.length.toLocaleString();
        }
    }

    return (
        <>
            <Text size="sm">Rows: </Text>
            <Text size="sm">{renderCounterText(table)}</Text>
        </>
    )
}
