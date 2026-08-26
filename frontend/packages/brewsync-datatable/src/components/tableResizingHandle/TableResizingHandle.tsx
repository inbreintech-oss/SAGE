import {Header, RowData, Table} from "@tanstack/react-table";
import {Box} from "@mantine/core";
import clsx from "clsx";
import classes from "./TableResizingHandle.module.css";

export type TableResizingHandleProps<TData extends RowData, TValue> = {
    table: Table<TData>;
    header: Header<TData, TValue>;
}

export default function TableResizingHandle<TData extends RowData, TValue>({
    table,
    header
}: TableResizingHandleProps<TData, TValue>) {
    return (
        <Box onDoubleClick={() => header.column.resetSize()}
             onMouseDown={header.getResizeHandler()}
             onTouchStart={header.getResizeHandler()}
             className={clsx({
                 [classes.tableResizingHandle]: true,
                 [classes.resizing]: table.getState().columnSizingInfo?.isResizingColumn === header.column.id
             })}
        />
    )
}
