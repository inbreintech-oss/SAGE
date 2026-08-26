import React from "react";
import {
    Row,
    RowData,
    Table,
    TableFeature,
} from "@tanstack/react-table";

/**
 * Row Click Handler Type
 */
export type RowClickHandler<TData extends RowData> = (row: TData, event: React.MouseEvent) => void;

/**
 * Row Click Options
 */
export interface RowClickOptions<TData extends RowData> {
    onRowClick?: RowClickHandler<TData>;
    onRowDoubleClick?: RowClickHandler<TData>;
}

/**
 * Row Click Row API
 */
export interface RowClickRow<TData extends RowData> {
    handleClick: (event: React.MouseEvent) => void;
    handleDoubleClick: (event: React.MouseEvent) => void;
}

/**
 * Row Click Feature
 */
export const RowClick: TableFeature = {
    getDefaultOptions: <TData extends RowData>(
        table: Table<TData>
    ): RowClickOptions<TData> => {
        return {
            onRowClick: undefined,
            onRowDoubleClick: undefined,
        }
    },

    createRow: <TData extends RowData>(
        row: Row<TData>,
        table: Table<TData>
    ): void => {
        row.handleClick = (event: React.MouseEvent) => {
            const { onRowClick } = table.options;
            if (onRowClick) {
                onRowClick(row.original, event);
            }
        };

        row.handleDoubleClick = (event: React.MouseEvent) => {
            const { onRowDoubleClick } = table.options;
            if (onRowDoubleClick) {
                onRowDoubleClick(row.original, event);
            }
        };
    }
};

declare module "@tanstack/react-table" {
    interface TableOptionsResolved<TData extends RowData> extends RowClickOptions<TData> {}
    interface Row<TData extends RowData> extends RowClickRow<TData> {}
}
