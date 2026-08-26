import { Anchor } from "@mantine/core";
import type { MdProps } from "../types";

export default function AnchorHandler({
    children,
    href,
    target,
    node,
    ...rest
}: MdProps<"a">) {
    let _target = "_blank";

    if (href?.startsWith("#")) {
        _target = "_self";
    }

    // TODO: Link Guard? 경고 추가
    return (
        <Anchor href={href} target={_target} {...rest}>
            {children}
        </Anchor>
    )
}