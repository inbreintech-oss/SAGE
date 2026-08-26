import React from "react";
import {Anchor, type AnchorProps} from "@mantine/core";
import {Link} from "react-router-dom";

export type AppAnchorProps = Readonly<{
    to?: string;
    children?: React.ReactNode;
} & Omit<AnchorProps, "href" | "component" | "children">>;

export default function AppAnchor({
    to,
    children,
    ...anchorProps
}: AppAnchorProps) {
    return (
        <Anchor to={to || "#"} component={Link} {...anchorProps}>
            {children}
        </Anchor>
    )
}