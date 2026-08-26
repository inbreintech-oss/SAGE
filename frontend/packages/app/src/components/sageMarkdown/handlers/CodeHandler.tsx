import type { MdProps } from "../types";
import { CodeHighlight, InlineCodeHighlight } from "@mantine/code-highlight";

export default function CodeHandler({
    children,
    className,
}: MdProps<"code">) {
    const match = /language-(\w+)/.exec(className ?? "");
    const lang = match && match[1] ? match[1] : undefined;
    const raw = String(children ?? "");
    // remark가 처리한 fenced code block은 항상 trailing \n이 붙음 → block code로 간주
    const isBlock = raw.endsWith("\n") || !!lang;
    const code = raw.replace(/\n$/, "");


    if (isBlock) {
        return (
            <CodeHighlight language={lang ?? "text"} code={code} my="sm" withBorder withExpandButton />
        )
    } else {
        return (
            <InlineCodeHighlight code={code} withBorder />
        )
    }
}