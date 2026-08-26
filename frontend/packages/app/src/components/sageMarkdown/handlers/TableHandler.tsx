import { Table } from "@mantine/core";
import type { MdProps } from "../types";

export function TableHandler({
    children,
}: MdProps<"table">) {
    return (
        <Table.ScrollContainer minWidth={300} my="sm">
            <Table>
                {children}
            </Table>
        </Table.ScrollContainer>
    )
}

export function TheadHandler({
    children,
}: MdProps<"thead">) {
    return (
        <Table.Thead>
            {children}
        </Table.Thead>
    )
}

export function TbodyHandler({
    children,
}: MdProps<"tbody">) {
    return (
        <Table.Tbody>
            {children}
        </Table.Tbody>
    )
}

export function TrHandler({
    children,
}: MdProps<"tr">) {
    return (
        <Table.Tr>
            {children}
        </Table.Tr>
    )
}

export function ThHandler({
    children,
    node,
}: MdProps<"th">) {
    const align = parseTableAlign(node?.properties.align?.toString() ?? "");
    return (
        <Table.Th align={align} bg="gray.1">
            {children}
        </Table.Th>
    )
}

export function TdHandler({
    children,
    node,
}: MdProps<"td">) {
    const align = parseTableAlign(node?.properties.align?.toString() ?? "");
    return (
        <Table.Td align={align}>
            {children}
        </Table.Td>
    )
}

type TableAlign = "left" | "center" | "right" | "justify" | "char" | undefined;
function parseTableAlign(alignText: string): TableAlign {
    switch(alignText) {
        case "left":
            return "left";
        case "center":
            return "center";
        case "right":
            return "right";
        case "justify":
            return "justify";
        case "char":
            return "char";
        default:
            return undefined;
    }
}