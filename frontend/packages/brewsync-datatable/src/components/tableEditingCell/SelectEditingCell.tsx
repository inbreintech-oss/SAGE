import { Cell, RowData, Table } from "@tanstack/react-table";
import { TableCell } from "@/components";
import { Select } from "@mantine/core";
import { DensityState } from "@/features/density";
import { useState } from "react";

export type SelectEditingCellProps<TData extends RowData> = {
    table: Table<TData>;
    cell: Cell<TData, string>;
    density: DensityState;
    options: Array<{ value: string; label: string }>;
    getCellValue?: (columnId: string, defaultValue: any) => any;
    updateCellValue?: (columnId: string, value: any) => void;
};

export default function SelectEditingCell<TData extends RowData>({
    table,
    cell,
    density,
    options,
    getCellValue,
    updateCellValue,
}: SelectEditingCellProps<TData>) {
    const error = cell.getEditingError();
    const initialValue = getCellValue 
        ? getCellValue(cell.column.id, cell.getValue() as string)
        : (cell.getEditingValue() as string) ?? "";
    
    const [value, setValue] = useState(initialValue);

    const handleChange = (newValue: string | null) => {
        const finalValue = newValue ?? "";
        setValue(finalValue);
        
        // ref 업데이트 (리렌더 없음)
        if (updateCellValue) {
            updateCellValue(cell.column.id, finalValue);
        }
    };

    return (
        <TableCell width={cell.column.getSize()} px={0} py={0}>
            <Select
                w="100%"
                size={density}
                value={value}
                onChange={handleChange}
                data={options}
                error={error}
                styles={{
                    root: { height: "100%" },
                    wrapper: { height: "100%" },
                    input: {
                        height: "100%",
                        minHeight: 0,
                        borderRadius: 0,
                        border: error ? "1px solid red" : "none"
                    }
                }}
            />
        </TableCell>
    );
}
