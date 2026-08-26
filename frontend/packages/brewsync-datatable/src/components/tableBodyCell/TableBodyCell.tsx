import React from "react";
import {MantineSpacing, StyleProp, Text} from "@mantine/core";
import {Cell, flexRender, type RowData, Table} from "@tanstack/react-table";
import {TableCell} from "@/components";
import {DensityState} from "@/features/density";
import {formatCellValue} from "@/utils/cellFormat";
// import classes from "./TableBodyCell.module.css";

export type TableBodyCellProps<TData extends RowData, TValue> = {
    table: Table<TData>;
    cell: Cell<TData, TValue>;
    density: DensityState;
}

export default function TableBodyCell<TData extends RowData, TValue>({
    table,
    cell,
    density,
}: TableBodyCellProps<TData, TValue>) {
    const {
        columnSizingInfo,
    } = table.getState();

    const isResizing = columnSizingInfo?.isResizingColumn === cell.column.id;

    let px: StyleProp<MantineSpacing> | undefined;
    let py: StyleProp<MantineSpacing> | undefined;
    switch (density) {
        default:
        case "md":
            px = "sm";
            py = "xs";
            break;
        case "sm":
        case "xs":
            px = "xs";
            py = 4;
            break;
    }

    // cellFormat이 있으면 포맷팅, 없으면 기본 렌더링
    const cellFormat = cell.column.columnDef.meta?.cellFormat;
    const cellValue = cell.getValue();

    let renderedContent;
    if (cellFormat) {
        // cellFormat이 있는 경우 포멧 처리
        renderedContent = formatCellValue(cellValue, cellFormat);
    } else {
        // 아닌 경우 일반 렌더링 처리
        renderedContent = flexRender(cell.column.columnDef.cell, cell.getContext());
    }

    const contentAlign = cell.column.columnDef.meta?.contentAlign;
    const justifyContent = contentAlign === "left" ? "flex-start"
        : contentAlign === "right" ? "flex-end"
        : contentAlign === "center" ? "center"
        : "flex-start";

    return (
        <TableCell width={cell.column.getSize()}
                   px={px}
                   py={py}
                   style={{ justifyContent }}
        >
            <Text size={density} truncate="end">
                {renderedContent}
            </Text>
        </TableCell>
    )
}

export const Memo_TableBodyCell = React.memo(
    TableBodyCell,
    (prev, next) =>
        prev.cell === next.cell &&
        prev.table === next.table &&
        prev.density === next.density
) as typeof TableBodyCell;
