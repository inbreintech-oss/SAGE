import {Row, RowData, Table} from "@tanstack/react-table";
import {ActionIcon, Group} from "@mantine/core";
import {IconDeviceFloppy, IconEdit, IconTrash, IconX} from "@tabler/icons-react";

export type RowEditActionCellProps<TData extends RowData> = {
    table: Table<TData>;
    row: Row<TData>;
    type: "edit" | "save" | "delete";
}

export default function RowEditActionCell<TData extends RowData>({
    table,
    row,
    type,
}: RowEditActionCellProps<TData>) {
    const {
        density,
    } = table.getState();

    const editing = row.getIsEditing();

    if (type === "edit") {
        if (editing) return null;
        return (
            <ActionIcon size={density === "xs" ? "sm" : "md"}
                        variant="subtle"
                        onClick={() => row.startEditing()}
                        aria-label="edit"
            >
                <IconEdit size={16} />
            </ActionIcon>
        );
    }

    if (type === "delete") {
        if (editing) return null;
        return (
            <ActionIcon size={density === "xs" ? "sm" : "md"}
                        variant="subtle"
                        color="red"
                        onClick={() => row.deleteRow()}
                        aria-label="delete"
            >
                <IconTrash size={16} />
            </ActionIcon>
        );
    }

    if (type === "save") {
        if (!editing) return null;
        return (
            <Group gap={4} wrap="nowrap" justify="center">
                <ActionIcon size={density === "xs" ? "sm" : "md"}
                            variant="subtle"
                            color="green"
                            onClick={() => row.saveEditing()}
                            aria-label="save"
                >
                    <IconDeviceFloppy size={16} />
                </ActionIcon>
                <ActionIcon size={density === "xs" ? "sm" : "md"}
                            variant="subtle"
                            color="gray"
                            onClick={() => row.cancelEditing()}
                            aria-label="cancel"
                >
                    <IconX size={16} />
                </ActionIcon>
            </Group>
        );
    }

    return null;
}
