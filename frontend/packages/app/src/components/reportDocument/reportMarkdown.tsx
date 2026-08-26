import Markdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import classes from "./reportDocument.module.css";

/**
 * CommonMark flanking 보정.
 *
 * `**29.98%**의` 처럼 닫는 `**` 직전이 구두점(`%`, `)`, `,` 등)이고
 * 직후가 글자·숫자면 right-flanking 이 성립하지 않아 별표가 그대로 남는다.
 * (예: `**기가레인:**` 은 직후가 `:` 라서 정상)
 *
 * 닫는 `**` 앞에 ZWSP(U+200B)를 넣어 파싱을 복구한다.
 */
export function normalizeReportMarkdownEmphasis(source: string): string {
    let out = "";
    let i = 0;
    while (i < source.length) {
        if (source.startsWith("**", i)) {
            const close = source.indexOf("**", i + 2);
            if (close < 0) {
                out += source.slice(i);
                break;
            }
            const inner = source.slice(i + 2, close);
            const next = source[close + 2] ?? "";
            const last = inner.at(-1) ?? "";
            const needsZwsp =
                inner.length > 0
                && !inner.includes("\n")
                && !inner.endsWith("\u200B")
                && /[\p{P}%]/u.test(last)
                && /^[\p{L}\p{N}]/u.test(next);

            out += needsZwsp ? `**${inner}\u200B**` : `**${inner}**`;
            i = close + 2;
            continue;
        }
        out += source[i];
        i += 1;
    }
    return out;
}

/**
 * 보고서 카드 전용 마크다운.
 * SageMarkdown(remark-math/katex) 미사용 — 수치 `%`·볼드 간섭 방지.
 */
const reportMdComponents: Components = {
    h1: ({ children }) => <h2 className={classes.mdH1}>{children}</h2>,
    h2: ({ children }) => <h3 className={classes.mdH2}>{children}</h3>,
    h3: ({ children }) => <h4 className={classes.mdH3}>{children}</h4>,
    h4: ({ children }) => <h5 className={classes.mdH4}>{children}</h5>,
    p: ({ children }) => <p className={classes.mdP}>{children}</p>,
    ul: ({ children }) => <ul className={classes.mdUl}>{children}</ul>,
    ol: ({ children }) => <ol className={classes.mdOl}>{children}</ol>,
    li: ({ children }) => <li className={classes.mdLi}>{children}</li>,
    strong: ({ children }) => <strong className={classes.mdStrong}>{children}</strong>,
    em: ({ children }) => <em className={classes.mdEm}>{children}</em>,
    blockquote: ({ children }) => (
        <blockquote className={classes.mdBlockquote}>{children}</blockquote>
    ),
    hr: () => <hr className={classes.mdHr} />,
};

export function ReportMarkdown({ children }: { children: string }) {
    const raw = typeof children === "string" ? children : String(children ?? "");
    const source = normalizeReportMarkdownEmphasis(raw);
    return (
        <Markdown remarkPlugins={[remarkGfm]} components={reportMdComponents}>
            {source}
        </Markdown>
    );
}
