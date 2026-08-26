import React from "react";
import {Flex, Group, Pagination, Select} from "@mantine/core";
import {RowData, Table} from "@tanstack/react-table";
import RowCounter from "@/components/tableToolBar/RowCounter";

export type TableToolBarProps<TData extends RowData> = {
    table: Table<TData>;
}

export default function TableToolBar<TData extends RowData>({
    table
}: TableToolBarProps<TData>) {
    const {
        enablePagination,
    } = table.options.meta || {};

    const handlePageChanged = (page: number) => {
        table.setPageIndex(page - 1);
    }

    const handlePageSizeChanged = (size: string | null) => {
        const nSize = Number(size ?? table.initialState.pagination.pageSize);
        table.setPageSize(nSize);
    }

    return (
        <Flex justify="space-between" px="xs">
            <Group gap="xs">
                <RowCounter table={table} />
                {enablePagination &&
                    <Select data={table.options.meta?.defaultPageSizes?.map(size => size.toString())}
                            value={table.getState().pagination.pageSize?.toString()}
                            onChange={(value) => handlePageSizeChanged(value)}
                            style={{width: 100}}
                    />
                }
            </Group>
            <Group>
                {enablePagination &&
                    <Pagination total={table.getPageCount()}
                                value={table.getState().pagination.pageIndex + 1}
                                onChange={handlePageChanged}

                    />
                }
            </Group>
        </Flex>
    )
}
