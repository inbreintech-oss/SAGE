import React from "react";
import {Box, Text} from "@mantine/core";

export type BaseColumnProps = Readonly<{
    children?: React.ReactNode;
    textAlign?: "left" | "center" | "right";
}>;

export default function BaseColumn({
    children,
    textAlign
}: BaseColumnProps) {
    return (
        <Box w="100%">
            <Text size="sm" truncate="end" ta={textAlign || "center"}>
                {children}
            </Text>
        </Box>
    )
}
