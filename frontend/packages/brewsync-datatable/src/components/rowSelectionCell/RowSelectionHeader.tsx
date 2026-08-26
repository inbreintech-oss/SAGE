import {Center, Checkbox} from "@mantine/core";
import {Table} from "@tanstack/react-table";

export type RowSelectionHeaderProps<TData> = {
    table: Table<TData>,
}

export default function RowSelectionHeader<TData>({
    table
}: RowSelectionHeaderProps<TData>) {
    const {
        density
    } = table.getState();

    return (
        <Center>
            <Checkbox size={density}
                      checked={table.getIsAllRowsSelected()}
                      indeterminate={table.getIsSomeRowsSelected()}
                      onChange={table.getToggleAllRowsSelectedHandler()}
            />
        </Center>
    )
}
