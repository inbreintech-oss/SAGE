import React, {useRef} from "react";
import {Box} from "@mantine/core";
import {
    EditingRow,
    Memo_TableBodyCell,
    TableBodyCell,
    TableHeader,
    TableRow
} from "@/components";
import {type RowData, type Table} from "@tanstack/react-table";
import {useVirtualizer} from "@tanstack/react-virtual";

export type TableBodyProps<TData extends RowData> = {
    table: Table<TData>;
}

export default function TableBody<TData extends RowData>({
    table,
}: TableBodyProps<TData>) {
    const rows = table.getRowModel().rows;
    const scrollRef = useRef<HTMLDivElement | null>(null);
    const rowVirtualizer = useVirtualizer({
        debug: true,
        count: rows.length,
        estimateSize: () => 45.8,
        getScrollElement: () => scrollRef.current,
        overscan: 5
    });

    const {
        columnSizingInfo,
        density,
        rowEditing,
    } = table.getState();

    return (
        <div ref={scrollRef} style={{overflowY: "scroll", willChange: "transform", contain: "paint"}}>
            <TableHeader table={table}/>
            <Box style={{
                height: rowVirtualizer.getTotalSize(),
                position: "relative",
            }}
            >
                {rowVirtualizer.getVirtualItems().map((virtualItem) => {
                    const row = rows[virtualItem.index];

                    const RowComponent = rowEditing[row.id] ? EditingRow : TableRow;

                    return (
                        <RowComponent key={virtualItem.key}
                                      index={virtualItem.index}
                                      ref={rowVirtualizer.measureElement}
                                      table={table}
                                      row={row}
                                      isHeader={false}
                                      style={{
                                          position: "absolute",
                                          transform: `translateY(${virtualItem.start}px)`
                                      }}
                        >
                            {row.getVisibleCells().map((cell) => {
                                if (columnSizingInfo?.isResizingColumn === cell.column.id) {
                                    return (
                                        <TableBodyCell key={cell.id}
                                                       table={table}
                                                       cell={cell}
                                                       density={density}/>
                                    )
                                } else {
                                    return (
                                        <Memo_TableBodyCell key={cell.id}
                                                            table={table}
                                                            cell={cell}
                                                            density={density}/>
                                    )
                                }
                            })}
                        </RowComponent>
                    )

                })}
            </Box>
        </div>
    )
}
