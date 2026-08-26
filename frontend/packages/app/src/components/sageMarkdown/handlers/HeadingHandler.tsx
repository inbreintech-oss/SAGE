import { Title, type TitleOrder } from "@mantine/core"
import type { MdProps } from "../types"

export default function HeadingHandler(order: TitleOrder) {
    return ({
        children,
        node,
        ...rest
    }: MdProps<"h1">) => {
        return (
            <Title order={order} mb="sm" {...rest}>
                {children}
            </Title>
        )
    }
}