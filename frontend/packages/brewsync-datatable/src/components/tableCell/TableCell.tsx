import React, {CSSProperties} from "react";
import {useDataTableContext} from "@/components";
import {Box, BoxProps} from "@mantine/core";
import clsx from "clsx";
import classes from "./TableCell.module.css";

export type TableCellProps = {
    width: CSSProperties["width"];
    children?: React.ReactNode;
    textAlign?: CSSProperties["textAlign"];
    resizing?: boolean;
} & BoxProps

export default function TableCell({
    width,
    textAlign,
    children,
    className,
    resizing,
    style,
    ...rest
}: TableCellProps) {
    const context = useDataTableContext();
    const {
        withColumnBorder
    } = context.meta;

    return (
        <Box w={width}
             ta={textAlign}
             px="sm"
             py="xs"
             style={{
                 display: "flex",
                 alignItems: "center",
                 position: "relative",
                 overflow: "hidden",
                 ...style,
             }}
             className={clsx({
                 [classes.tableCell]: true,
                 [classes.withColBorders]: withColumnBorder === true,
                 [classes.resizing]: !!resizing,
             }, className)}
             {...rest}
        >
            {children}
        </Box>
    )
}
