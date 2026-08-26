import type { Components } from "react-markdown";
import {
    AnchorHandler,
    BlockquoteHandler,
    CodeHandler,
    HeadingHandler,
    ImageHandler,
    InputHandler,
    // ListHandler,
    ParagraphHandler,
    SpanHandler,
    TableHandler
} from "./";

const mdComponentDef: Components = {
    h1: HeadingHandler(1),
    h2: HeadingHandler(2),
    h3: HeadingHandler(3),
    h4: HeadingHandler(4),
    h5: HeadingHandler(5),
    h6: HeadingHandler(6),
    p: ParagraphHandler("p"),
    strong: SpanHandler("strong"),
    del: SpanHandler("del"),
    blockquote: BlockquoteHandler,
    // ul: ListHandler.UlHandler,
    // ol: ListHandler.OlHandler,
    // li: ListHandler.LiHandler,
    input: InputHandler,
    code: CodeHandler,
    a: AnchorHandler,
    table: TableHandler.TableHandler,
    thead: TableHandler.TheadHandler,
    tbody: TableHandler.TbodyHandler,
    tr: TableHandler.TrHandler,
    th: TableHandler.ThHandler,
    td: TableHandler.TdHandler,
    img: ImageHandler,  
}

export default mdComponentDef;