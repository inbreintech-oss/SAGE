import React from "react";
import {flexRender, type Header, type Table} from "@tanstack/react-table";
import {Flex, MantineSpacing, StyleProp, Text} from "@mantine/core";
import type {TextAlign} from "@/types";
import {SortIcon, FilterPopover, TableCell, TableResizingHandle} from "@/components";
import clsx from "clsx";
import classes from "./TableHeaderCell.module.css";
import {DensityState} from "@/features/density";

export type TableHeaderCell<TData, TValue> = {
    table: Table<TData>;
    header: Header<TData, TValue>;
    density: DensityState;
};

export default function TableHeaderCell<TData, TValue>({
    table,
    header,
    density,
}: TableHeaderCell<TData, TValue>) {
    const canSort = header.column.getCanSort() && table.options.enableSorting;
    const canFilter = header.column.getCanFilter() && table.options.enableColumnFilters;
    const canResize = header.column.getCanResize() && table.options.enableColumnResizing;

    const textAlignToJustify = (align?: TextAlign) => {
        switch (align) {
            case "center":
                return "center";
            case "left":
                return "flex-start";
            case "right":
                return "flex-end";
            default:
                return "";
        }
    }

    const toggleSort = (e: React.MouseEvent) => {
        if (canSort) {
            header.column.getToggleSortingHandler()?.(e);
        }
    }

    const {
        columnSizingInfo,
    } = table.getState();

    const isResizing = columnSizingInfo?.isResizingColumn === header.column.id;

    let px: StyleProp<MantineSpacing> | undefined;
    let py: StyleProp<MantineSpacing> | undefined;
    switch (density) {
        default:
        case "md":
            px = "sm";
            py = "xs";
            break;
        case "sm":
        case "xs":
            px = "xs";
            py = 4;
            break;
    }

    return (
        <TableCell width={header.getSize()}
                   className={clsx({
                       [classes.withHandle]: canResize
                   })}
                   px={px} py={py}
        >
            <Flex gap={(canSort || canFilter || canResize) ? 4 : 0}
                  align="center"
                  h="100%"
                  w="100%"
            >
                <Flex align="center"
                      justify={(canSort || canFilter || canResize) ?
                          textAlignToJustify(header.column.columnDef.meta?.headerAlign) :
                          "center"
                      }
                      style={{
                          ...(canSort && {
                              cursor: "pointer",
                          }),
                          ...((canSort || canResize) && {
                              userSelect: "none",
                          })
                      }} flex={1} miw={0}
                      onClick={toggleSort}
                >
                    {header?.getContext() && (
                        <Text size={density} fw={"bold"} truncate="end">
                            {header.isPlaceholder
                                ? null
                                : flexRender(
                                    header.column.columnDef.header,
                                    header.getContext()
                                )
                            }
                        </Text>
                    )}
                </Flex>
                <Flex>
                    {canSort &&
                        <SortIcon direction={header.column.getIsSorted()} onClick={toggleSort}/>
                    }
                    {canFilter &&
                        <FilterPopover column={header.column}/>
                    }
                </Flex>
            </Flex>
            {canResize &&
                <TableResizingHandle table={table} header={header}/>
            }
        </TableCell>
    )
}

export const Memo_TableHeaderCell = React.memo(
    TableHeaderCell,
    (prev, next) =>
        prev.header === next.header &&
        prev.table === next.table &&
        prev.density === next.density
);
