import { Text, type TextProps } from "@mantine/core";
import type { MdProps } from "../types";

export default function SpanHandler(type: React.ElementType) {
    return ({
        children,
        ...rest
    }: MdProps<"span">) => {
        const textProps: TextProps = {}

        switch (type) {
            case "p":
                break;
            case "strong":
                textProps.fw = "bold";
                break;
            case "del":
                textProps.td = "line-through";
                break;
        }

        return (
            <Text component="span" {...textProps} {...rest}>
                {children}
            </Text>
        )
    }
}