import { List } from "@mantine/core";
import type { MdProps } from "../types";

export function UlHandler({
    children,
}: MdProps<"ul">) {
    return (
        <List mb="sm">
            {children}
        </List>
    )
}

export function OlHandler({
    children,
    itemType,
}: MdProps<"ol">) {
    return (
        <List type="ordered" mb="sm" itemType={itemType}>
            {children}
        </List>
    )
}

export function LiHandler({
    children,
}: MdProps<"li">) {
    return (
        <List.Item>
            {children}
        </List.Item>
    )
}