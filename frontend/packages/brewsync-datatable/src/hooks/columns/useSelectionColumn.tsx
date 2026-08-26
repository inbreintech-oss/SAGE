import {ColumnDef, RowData, TableOptions} from "@tanstack/react-table";
import {RowSelectionCell, RowSelectionHeader} from "@/components";

export function useSelectionColumn<TData extends RowData>(
    options: TableOptions<TData>
): ColumnDef<TData> | null {
    return {
        id: "__selection_column__",
        maxSize: 75,
        enableResizing: false,
        meta: {
            contentAlign: "center",
            enableEditing: false,
        },
        cell: ({row, table}) => {
            const {density} = table.getState();
            return (
                <RowSelectionCell row={row}
                                  table={table}
                                  isSelected={row.getIsSelected()}
                                  density={density}/>
            );
        },
        header: ({table}) => options.enableMultiRowSelection && <RowSelectionHeader table={table}/>
    }
}
