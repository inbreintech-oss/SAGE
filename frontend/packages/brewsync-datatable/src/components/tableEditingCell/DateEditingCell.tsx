import { Cell, RowData, Table } from "@tanstack/react-table";
import { TableCell } from "@/components";
import { DateInput, DateTimePicker } from "@mantine/dates";
import { DensityState } from "@/features/density";
import { useState } from "react";
import dayjs from "dayjs";

export type DateEditingCellProps<TData extends RowData> = {
    table: Table<TData>;
    cell: Cell<TData, Date | string>;
    density: DensityState;
    getCellValue?: (columnId: string, defaultValue: any) => any;
    updateCellValue?: (columnId: string, value: any) => void;
    dateFormat?: string;
    withSeconds?: boolean;
};

export default function DateEditingCell<TData extends RowData>({
    table,
    cell,
    density,
    getCellValue,
    updateCellValue,
    dateFormat,
    withSeconds = false,
}: DateEditingCellProps<TData>) {
    const error = cell.getEditingError();
    // withSeconds에 따라 기본 포맷 설정
    const defaultFormat = withSeconds ? 'YYYY-MM-DD HH:mm:ss' : 'YYYY-MM-DD';
    const format = dateFormat || defaultFormat;

    const rawValue = getCellValue
        ? getCellValue(cell.column.id, cell.getValue())
        : cell.getEditingValue();

    // Date 객체나 날짜 문자열을 지정된 형식으로 변환
    const initialValue = rawValue
        ? dayjs(rawValue).format(format)
        : null;

    const [value, setValue] = useState<string | null>(initialValue);

    const handleChange = (newValue: string | null) => {
        const formattedValue = newValue ? dayjs(newValue).format(format) : null;
        setValue(formattedValue);

        // ref 업데이트 (리렌더 없음)
        if (updateCellValue) {
            updateCellValue(cell.column.id, formattedValue);
        }
    };

    const commonStyles = {
        root: { height: "100%" },
        wrapper: { height: "100%" },
        input: {
            height: "100%",
            minHeight: 0,
            borderRadius: 0,
            border: error ? "1px solid red" : "none"
        }
    };

    // string value를 Date로 변환 (컴포넌트 입력용)
    const dateValue = value ? dayjs(value, format).toDate() : null;

    return (
        <TableCell width={cell.column.getSize()} px={0} py={0}>
            {withSeconds ? (
                <DateTimePicker
                    size={density}
                    value={dateValue}
                    onChange={handleChange}
                    valueFormat={format}
                    withSeconds={withSeconds}
                    error={error}
                    styles={commonStyles}
                />
            ) : (
                <DateInput
                    size={density}
                    value={dateValue}
                    onChange={handleChange}
                    valueFormat={format}
                    error={error}
                    styles={commonStyles}
                />
            )}
        </TableCell>
    );
}
