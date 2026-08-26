import React from "react";
import {Flex, MantineStyleProp} from "@mantine/core";
import clsx from "clsx";
import classes from "./TableRow.module.css";
import {useDataTableContext} from "@/components";
import {Row, RowData, Table} from "@tanstack/react-table";

export type TableRowProps<TData extends RowData = any> = {
    table: Table<TData>;
    row?: Row<TData>;
    ref?: React.Ref<HTMLDivElement>;
    index?: number;
    children?: React.ReactNode;
    isHeader?: boolean;
    style?: MantineStyleProp;
}

export default function TableRow<TData extends RowData = any>({
    ref,
    index,
    children,
    isHeader,
    style,
    table,
    row,
}: TableRowProps<TData>) {
    const context = useDataTableContext();
    const {
        withRowBorder,
        withStripe,
        withHighlightOnHover,
    } = context.meta;

    // index is zero based index.
    let striped = false;
    if (withStripe !== undefined && index !== undefined) {
        if (withStripe === "even" && index % 2 === 1)  {
            striped = true;
        } else if (withStripe === "odd" && index % 2 === 0)  {
            striped = true;
        }
    }

    const handleClick = (e: React.MouseEvent) => {
        if (!isHeader && row) {
            row.handleClick(e);
        }
    };

    const handleDoubleClick = (e: React.MouseEvent) => {
        if (!isHeader && row) {
            row.handleDoubleClick(e);
        }
    };

    // row click/dblclick 핸들러가 있는지 확인
    const hasClickHandlers = !isHeader && (
        table.options.onRowClick || table.options.onRowDoubleClick
    );

    return (
        <Flex ref={ref}
              className={clsx({
                  [classes.tableRow]: true,
                  [classes.withRowBorders]: withRowBorder === true,
                  [classes.header]: isHeader,
                  [classes.hightlightOnHover]: withHighlightOnHover,
                  [classes.striped]: striped,
                  [classes.clickable]: hasClickHandlers,
              })}
              data-index={index}
              style={{...style}}
              onClick={handleClick}
              onDoubleClick={handleDoubleClick}
        >
            {children}
        </Flex>
    )
}
