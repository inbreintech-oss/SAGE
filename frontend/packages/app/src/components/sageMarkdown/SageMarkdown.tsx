import Markdown, {type Options} from "react-markdown";
import { mdComponentDef } from "./handlers";
import { SageMarkdownDataContext, type SageMarkdownData } from "./SageMarkdownDataContext";

// import plugins
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import remarkDisableIndentedCodeBlocks from "./plugins/remarkDisableIndentedCodeBlocks";

export type SageMarkdownProps = Readonly<{
    data?: SageMarkdownData;
} & Options>;

export default function SageMarkdown({
    children,
    components,
    remarkPlugins,
    rehypePlugins,
    data,
    ...rest
}: SageMarkdownProps) {
    return (
        <SageMarkdownDataContext.Provider value={data ?? {}}>
            <Markdown {...rest}
                      rehypePlugins={[rehypeKatex, ...(rehypePlugins ?? [])]}
                      remarkPlugins={[remarkDisableIndentedCodeBlocks, remarkGfm, remarkMath, ...(remarkPlugins ?? [])]}
                      components={{
                          ...mdComponentDef,
                          ...components
                      }}
            >
                {children}
            </Markdown>
        </SageMarkdownDataContext.Provider>
    )
}