import React from "react";
import {Flex} from "@mantine/core";
import {RowData, Table as ReactTable} from "@tanstack/react-table";
import {TableBody, TableToolBar, useDataTableContext} from "@/components";
import clsx from "clsx";
import classes from "./Table.module.css";

export type TableProps<TData extends RowData> = {
    table: ReactTable<TData>;
}

export default function Table<TData extends RowData>({
    table,
}: TableProps<TData>) {
    const {
        tableWidth,
        tableHeight,
        withTableBorder
    } = useDataTableContext().meta;

    return (
        <Flex direction="column"
              w={tableWidth || "100%"}
              h={tableHeight || "100%"}
              pt="xs"
              gap={"xs"}
              className={clsx({
                  [classes.tableWrap]: true
              })}
        >
            <TableToolBar table={table}/>
            <Flex direction="column"
                  flex={1}
                  mih={0}
                  className={clsx({
                      [classes.table]: true,
                      [classes.withTableBorder]: withTableBorder === true,
                  })}
            >
                <TableBody table={table}/>
            </Flex>
        </Flex>
    )
}
