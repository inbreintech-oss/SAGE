import type { MdProps } from "../types";
import {Image} from "@mantine/core";

export default function ImageHandler({
    children,
    src,
    alt,
    node,
    ...rest
}: MdProps<"img">) {
    return (
        <Image alt={alt} src={src} {...rest} />
    )
}