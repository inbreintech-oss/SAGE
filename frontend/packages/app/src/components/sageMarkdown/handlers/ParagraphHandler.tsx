import React from "react";
import { Text, type TextProps } from "@mantine/core";
import type { MdProps } from "../types";
import PlaceholderHandler from "./PlaceholderHandler";

const PLACEHOLDER_REGEX = /\[\[([a-zA-Z0-9_-]+)]]|\[([a-zA-Z0-9_-]+)]/g;

type Segment = { kind: "text"; value: React.ReactNode } | { kind: "placeholder"; id: string };

function segmentChildren(children: React.ReactNode): Segment[] {
    const segments: Segment[] = [];

    React.Children.forEach(children, (child) => {
        if (typeof child !== "string") {
            segments.push({ kind: "text", value: child });
            return;
        }

        let lastIndex = 0;
        for (const match of child.matchAll(PLACEHOLDER_REGEX)) {
            if (match.index > lastIndex) {
                segments.push({ kind: "text", value: child.slice(lastIndex, match.index) });
            }
            segments.push({ kind: "placeholder", id: match[1] ?? match[2] });
            lastIndex = match.index + match[0].length;
        }
        if (lastIndex < child.length) {
            segments.push({ kind: "text", value: child.slice(lastIndex) });
        }
    });

    return segments;
}

export default function ParagraphHandler(type: React.ElementType) {
    return ({
        children,
        node,
        ...rest
    }: MdProps<"p">) => {
        const textProps: TextProps = {}
        let componentType: React.ElementType = "p";

        switch (type) {
            case "p":
                componentType = "p";
                break;
        }

        const segments = segmentChildren(children);
        const hasPlaceholder = segments.some(s => s.kind === "placeholder");

        if (!hasPlaceholder) {
            return (
                <Text component={componentType} {...textProps} mb="sm" {...rest}>
                    {children}
                </Text>
            );
        }

        // placeholder가 있으면 Text 구간과 PlaceholderHandler를 fragment로 병렬 배치
        const nodes: React.ReactNode[] = [];
        let textBuffer: React.ReactNode[] = [];

        segments.forEach((seg, i) => {
            if (seg.kind === "text") {
                textBuffer.push(seg.value);
            } else {
                if (textBuffer.length > 0) {
                    nodes.push(
                        <Text key={`text-${i}`} component={componentType} mb="sm" {...textProps}>
                            {textBuffer}
                        </Text>
                    );
                    textBuffer = [];
                }
                nodes.push(<PlaceholderHandler key={`ph-${i}`} id={seg.id} />);
            }
        });

        if (textBuffer.length > 0) {
            nodes.push(
                <Text key="text-last" component={componentType} mb="sm" {...textProps}>
                    {textBuffer}
                </Text>
            );
        }

        return <>{nodes}</>;
    }
}
