import {ColumnDef, RowData, TableOptions} from "@tanstack/react-table";
import RowEditActionCell from "@/components/rowEditActionCell/RowEditActionCell";

export function useEditActionColumn<TData extends RowData>(
    options: TableOptions<TData>
): ColumnDef<TData>[] {
    return [
        {
            id: "__edit_action_column__",
            header: "수정",
            size: 60,
            enableResizing: false,
            meta: {
                contentAlign: "center",
                enableEditing: false,
            },
            cell: ({row, table}) => (
                <RowEditActionCell row={row} table={table} type="edit" />
            ),
        },
        {
            id: "__delete_action_column__",
            header: "삭제",
            size: 60,
            enableResizing: false,
            meta: {
                contentAlign: "center",
                enableEditing: false,
            },
            cell: ({row, table}) => (
                <RowEditActionCell row={row} table={table} type="delete" />
            ),
        },
        {
            id: "__save_action_column__",
            header: "저장",
            size: 100,
            enableResizing: false,
            meta: {
                contentAlign: "center",
                enableEditing: false,
            },
            cell: ({row, table}) => (
                <RowEditActionCell row={row} table={table} type="save" />
            ),
        }
    ]
}
