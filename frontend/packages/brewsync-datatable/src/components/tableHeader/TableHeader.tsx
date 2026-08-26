import {Table} from "@tanstack/react-table";
import {Flex} from "@mantine/core";
import {TableHeaderCell, TableRow, useDataTableContext} from "@/components";
import clsx from "clsx";
import classes from "./TableHeader.module.css";

export type TableHeaderProps<TData> = {
    table: Table<TData>
}

export default function TableHeader<TData>({
    table,
}: TableHeaderProps<TData>) {
    const {
        stickyHeader
    } = useDataTableContext().meta;
    const {
        columnSizingInfo,
        density,
    } = table.getState()

    return (
        <Flex direction="column"
              className={clsx({
                  [classes.sticky]: stickyHeader
              })}
        >
            {table.getHeaderGroups().map(headerGroup => (
                <TableRow table={table} key={headerGroup.id} isHeader>
                    {headerGroup.headers.map((header) => (
                        // columnSizingInfo?.isResizingColumn == header.column.id ?
                        //     <TableHeaderCell key={header.id} table={table} header={header}/> :
                        //     <Memo_TableHeaderCell key={header.id} table={table} header={header}/>
                        <TableHeaderCell key={header.id} table={table} header={header} density={density} />
                    ))}
                </TableRow>
            ))}
        </Flex>
    )
}
