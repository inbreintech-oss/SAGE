import React from "react";
import {Checkbox} from "@mantine/core";
import {Row, Table} from "@tanstack/react-table";

export type RowSelectionCellProps<TData, _TValue> = {
    row: Row<TData>
    table: Table<TData>
    isSelected: boolean
    density: string
}

function RowSelectionCell<TData, TValue>({
    row,
    table,
    isSelected,
    density
}: RowSelectionCellProps<TData, TValue>) {
    return (
        <Checkbox size={density}
                  checked={isSelected}
                  disabled={!row.getCanSelect()}
                  onChange={row.getToggleSelectedHandler()}
        />
    )
}

export default React.memo(RowSelectionCell, (prev, next) => {
    return prev.isSelected === next.isSelected && 
           prev.density === next.density &&
           prev.row.id === next.row.id;
}) as typeof RowSelectionCell;
