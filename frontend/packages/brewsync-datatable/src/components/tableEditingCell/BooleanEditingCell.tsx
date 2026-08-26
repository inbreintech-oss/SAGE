import { Cell, RowData, Table } from "@tanstack/react-table";
import { TableCell } from "@/components";
import { Checkbox } from "@mantine/core";
import { DensityState } from "@/features/density";
import { useState } from "react";

export type BooleanEditingCellProps<TData extends RowData> = {
    table: Table<TData>;
    cell: Cell<TData, boolean>;
    density: DensityState;
    getCellValue?: (columnId: string, defaultValue: any) => any;
    updateCellValue?: (columnId: string, value: any) => void;
};

export default function BooleanEditingCell<TData extends RowData>({
    table,
    cell,
    density,
    getCellValue,
    updateCellValue,
}: BooleanEditingCellProps<TData>) {
    const initialValue = getCellValue
        ? getCellValue(cell.column.id, cell.getValue() as boolean)
        : (cell.getEditingValue() as boolean) ?? false;

    const [value, setValue] = useState(initialValue);

    const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const newValue = event.currentTarget.checked;
        setValue(newValue);

        // ref 업데이트 (리렌더 없음)
        if (updateCellValue) {
            updateCellValue(cell.column.id, newValue);
        }
    };

    const contentAlign = cell.column.columnDef.meta?.contentAlign;
    const justifyContent = contentAlign === "left" ? "flex-start"
        : contentAlign === "right" ? "flex-end"
        : contentAlign === "center" ? "center"
        : "flex-start";

    return (
        <TableCell width={cell.column.getSize()} px={0} py={0} style={{ justifyContent }}>
            <Checkbox
                checked={value}
                onChange={handleChange}
                styles={{
                    root: {
                        height: "100%",
                        display: "flex",
                        alignItems: "center",
                        paddingLeft: "var(--mantine-spacing-xs)",
                        paddingRight: "var(--mantine-spacing-xs)",
                    },
                }}
            />
        </TableCell>
    );
}
