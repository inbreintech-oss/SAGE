import {Column, RowData} from "@tanstack/react-table";
import {ActionIcon, Popover} from "@mantine/core";
import React, {useState} from "react";
import {IconFilter, IconFilterEdit} from "@tabler/icons-react";
import {TextFilter} from "@/components/tableFilter";

export type FilterPopoverProps<TData extends RowData> = {
    column: Column<TData, any>;
    filterType?: FilterType;
}

// TODO: 이후 여러 타입으로 생성 필요
export type FilterType = "text" | "select" | "date" | "text-range" | "date-range";

export default function FilterPopover<TData extends RowData>({
    column,
    filterType = "text",
}: FilterPopoverProps<TData>) {
    const [opened, setOpened] = useState<boolean>(false);

    const onSubmit = (value: any) => {
        column.setFilterValue(value);
        setOpened(false);
    }

    const onDismiss = () => {
        setOpened(false);
    }

    const onReset = () => {
        column.setFilterValue(undefined);
        setOpened(false);
    }

    const renderFilter = (type: FilterType) => {
        switch (type) {
            default:
            case "text":
                return (
                    <TextFilter value={column.getFilterValue()}
                                onSubmit={onSubmit}
                                onDismiss={onDismiss}
                                onReset={onReset}
                    />
                )
        }
    }

    return (
        <Popover opened={opened}
                 onChange={setOpened}
                 trapFocus
                 withArrow
        >
            <Popover.Target>
                <ActionIcon variant="transparent"
                            size={24}
                            onClick={() => setOpened(!opened)}
                >
                    {column.getIsFiltered() ?
                        <IconFilterEdit size={12} /> :
                        <IconFilter size={12} />
                    }
                </ActionIcon>
            </Popover.Target>
            <Popover.Dropdown p={0}>
                {renderFilter(filterType)}
            </Popover.Dropdown>
        </Popover>
    )
}
