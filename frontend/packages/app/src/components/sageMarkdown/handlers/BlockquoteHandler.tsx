import { Blockquote } from "@mantine/core";
import type { MdProps } from "../types";

export default function BlockquoteHandler({
    children
}: MdProps<"blockquote">) {
    return (
        <Blockquote p="md" my="md">
            {children}
        </Blockquote>
    )
}