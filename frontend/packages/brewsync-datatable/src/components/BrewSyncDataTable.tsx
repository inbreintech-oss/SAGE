import React from "react";
import {BrewSyncTableOptions, Xor} from "@/types";
import {type RowData, type Table as ReactTable} from "@tanstack/react-table";
import {DataTable} from "@/components";
import {useDataTable} from "@/hooks";

export type DataTableInstanceProps<TData extends RowData> = {
    table: ReactTable<TData>;
}

export type BrewSyncDataTableProps<TData extends RowData> = Xor<
    DataTableInstanceProps<TData>,
    BrewSyncTableOptions<TData>
>

export default function BrewSyncDataTable<TData extends RowData>(props: BrewSyncDataTableProps<TData>) {
    let table: ReactTable<TData>;

    if (props.table !== undefined) {
        table = props.table;
    } else {
        table = useDataTable(props);
    }

    return (
        <DataTable table={table} />
    )
}
