import { Checkbox } from "@mantine/core";
import type { MdProps } from "../types";

export default function InputHandler({
    type,
    node,
    ...rest
}: MdProps<"input">) {
    if (type ==="checkbox") {
        const {checked} = rest;

        return (
            <Checkbox checked={checked}
                      readOnly
                      style={{
                          display: "inline-block",
                          verticalAlign: "middle"
                      }}
            />
        )
    }
}