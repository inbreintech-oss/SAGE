import type {BrewSyncTableOptions} from "@/types";
import {
    getCoreRowModel,
    getPaginationRowModel,
    getFilteredRowModel,
    getSortedRowModel,
    type RowData, type TableMeta,
} from "@tanstack/react-table";
import {useMemo} from "react";

/**
 * 기본 값을 포함한 DataTableOptions를 생성합니다.
 */
export function useDataTableOptions<TData extends RowData>(defOptions: BrewSyncTableOptions<TData>): BrewSyncTableOptions<TData> {
    const {
        enablePagination = true,
        enableSorting = true,
        enableColumnFilters = true,
        enableGlobalFilter,
        enableColumnResizing = true,
        enableRowSelection = true,
        enableMultiRowSelection = false,
        enableRowEditing = true,
        enableDelete = true,
        columnResizeMode = "onChange",
        tableWidth = "100%",
        tableHeight = "100%",
        withTableBorder = true,
        withColumnBorder = true,
        withRowBorder = true,
        withStripe = "odd",
        withHighlightOnHover = true,
        stickyHeader = true,
        defaultPageSizes = ["25", "50", "100"],
        ...rest
    } = defOptions;

    const enableFilters = defOptions.enableFilters || (enableColumnFilters || enableGlobalFilter);

    const meta = useMemo<TableMeta<TData>>(() => {
        return {
            tableWidth,
            tableHeight,
            enablePagination,
            enableDelete,
            withTableBorder,
            withColumnBorder,
            withRowBorder,
            withStripe,
            withHighlightOnHover,
            stickyHeader,
            defaultPageSizes,
        }
    }, [])

    return {
        ...rest,
        meta,
        // initial values
        enableSorting,
        enableFilters,
        enableGlobalFilter,
        enableColumnFilters,
        enableColumnResizing,
        enableRowSelection,
        enableMultiRowSelection,
        enableRowEditing,
        columnResizeMode,
        getCoreRowModel: getCoreRowModel(),
        getSortedRowModel: enableSorting ? getSortedRowModel() : undefined,
        getPaginationRowModel: enablePagination ? getPaginationRowModel() : undefined,
        getFilteredRowModel: enableFilters ?
            getFilteredRowModel() :
            undefined,
    }
}
