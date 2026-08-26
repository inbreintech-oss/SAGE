import {
    TableBodyCell,
    TableRow,
    TextEditingCell,
    SelectEditingCell,
    DateEditingCell,
    BooleanEditingCell,
    CodePickerEditingCell
} from "@/components";
import { Cell, Row, RowData, Table } from "@tanstack/react-table";
import React, { useRef, useEffect } from "react";
import { MantineStyleProp } from "@mantine/core";

export type EditingRowProps<TData extends RowData> = {
    table: Table<TData>;
    row: Row<TData>;

    ref?: React.Ref<HTMLDivElement>;
    index?: number;
    children?: React.ReactNode;
    isHeader?: boolean;
    style?: MantineStyleProp;
}

export default function EditingRow<TData extends RowData>({
    table,
    row,
    ...rest
}: EditingRowProps<TData>) {
    const { density } = table.getState();
    
    // 편집 데이터를 로컬 state로 관리
    const editingDataRef = useRef<Record<string, any>>(row.getEditingData() || {});
    
    // 셀 값 업데이트 함수 (테이블 리렌더 없음)
    const updateCellValue = (columnId: string, value: any) => {
        editingDataRef.current[columnId] = value;
    };
    
    // 셀 값 가져오기 함수
    const getCellValue = (columnId: string, defaultValue: any) => {
        return editingDataRef.current[columnId] ?? defaultValue;
    };

    const renderCell = (cell: Cell<TData, unknown>) => {
        const meta = cell.column.columnDef.meta;

        // 편집 불가능한 컬럼은 일반 셀로 렌더링
        if (meta?.enableEditing === false) {
            return (
                <TableBodyCell
                    key={cell.id}
                    table={table}
                    cell={cell}
                    density={density}
                />
            );
        }

        // editingConfig 사용 (기본값: text)
        const config = meta?.editingConfig || { type: "text" };

        // 컬럼 타입에 따라 적절한 편집 셀 렌더링
        switch (config.type) {
            case "select":
                return (
                    <SelectEditingCell
                        key={cell.id}
                        table={table}
                        cell={cell as Cell<TData, string>}
                        density={density}
                        options={config.options}
                        getCellValue={getCellValue}
                        updateCellValue={updateCellValue}
                    />
                );

            case "date":
                return (
                    <DateEditingCell
                        key={cell.id}
                        table={table}
                        cell={cell as Cell<TData, Date | string>}
                        density={density}
                        getCellValue={getCellValue}
                        updateCellValue={updateCellValue}
                        dateFormat={config.format}
                        withSeconds={config.withSeconds}
                    />
                );

            case "boolean":
                return (
                    <BooleanEditingCell
                        key={cell.id}
                        table={table}
                        cell={cell as Cell<TData, boolean>}
                        density={density}
                        getCellValue={getCellValue}
                        updateCellValue={updateCellValue}
                    />
                );

            case "codePicker":
                return (
                    <CodePickerEditingCell
                        key={cell.id}
                        table={table}
                        cell={cell as Cell<TData, string | string[]>}
                        density={density}
                        codeGroupId={config.codeGroupId}
                        companyAppId={config.companyAppId}
                        mode={config.mode}
                        multiple={config.multiple}
                        codeColumnId={config.codeColumnId}
                        valueColumnId={config.valueColumnId}
                        query={config.query}
                        data={config.data}
                        resolveLabel={config.resolveLabel}
                        getCellValue={getCellValue}
                        updateCellValue={updateCellValue}
                    />
                );

            case "text":
            default:
                return (
                    <TextEditingCell
                        key={cell.id}
                        table={table}
                        cell={cell as Cell<TData, string>}
                        density={density}
                        getCellValue={getCellValue}
                        updateCellValue={updateCellValue}
                    />
                );
        }
    };

    // Save/Cancel 시 편집 데이터를 테이블 상태에 동기화
    useEffect(() => {
        const originalSave = row.saveEditing;
        const originalCancel = row.cancelEditing;
        
        row.saveEditing = async () => {
            // 모든 변경사항 반영 (테이블 상태 업데이트)
            const finalData = {
                ...(row.getEditingData() || {}),
                ...editingDataRef.current
            };
            
            table.setRowEditing(old => ({
                ...old,
                [row.id]: finalData
            }));
            
            // 최신 데이터를 직접 넘겨줌
            await originalSave.call(row, finalData);
        };
        
        return () => {
            row.saveEditing = originalSave;
            row.cancelEditing = originalCancel;
        };
    }, [row, table]);

    return (
        <TableRow table={table} row={row} {...rest}>
            {row.getVisibleCells().map((cell) => renderCell(cell))}
        </TableRow>
    );
}
