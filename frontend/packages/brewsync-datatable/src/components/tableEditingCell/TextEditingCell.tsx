import { Cell, RowData, Table } from "@tanstack/react-table";
import { TableCell } from "@/components";
import { TextInput } from "@mantine/core";
import { DensityState } from "@/features/density";
import { useState } from "react";

export type TextEditingCellProps<TData extends RowData> = {
    table: Table<TData>;
    cell: Cell<TData, string>;
    density: DensityState;
    getCellValue?: (columnId: string, defaultValue: any) => any;
    updateCellValue?: (columnId: string, value: any) => void;
};

export default function TextEditingCell<TData extends RowData>({
    table,
    cell,
    density,
    getCellValue,
    updateCellValue,
}: TextEditingCellProps<TData>) {
    const error = cell.getEditingError();
    const initialValue = getCellValue
        ? getCellValue(cell.column.id, cell.getValue() as string)
        : (cell.getEditingValue() as string) ?? "";

    const [value, setValue] = useState(initialValue);
    const config = cell.column.columnDef.meta?.editingConfig as any;
    const maxLength = config?.maxLength;

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const newValue = e.target.value;
        setValue(newValue);

        // ref 업데이트 (리렌더 없음)
        if (updateCellValue) {
            updateCellValue(cell.column.id, newValue);
        }
    };

    return (
        <TableCell width={cell.column.getSize()} px={0} py={0}>
            <TextInput w="100%"
                       size={density}
                       value={value}
                       onChange={handleChange}
                       error={error}
                       maxLength={maxLength}
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
