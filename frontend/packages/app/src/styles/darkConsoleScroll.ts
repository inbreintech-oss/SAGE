/** 다크 콘솔·코드 영역 공통 Mantine ScrollArea 스타일 (보고서 API 로그 기준) */
export const DARK_CONSOLE_SCROLL_STYLES = {
    viewport: { padding: "10px 12px" },
    scrollbar: {
        borderTop: "none",
        background: "transparent",
    },
    thumb: {
        background: "rgba(148, 163, 184, 0.35)",
    },
} as const;

export const DARK_CONSOLE_SCROLL_PROPS = {
    type: "hover" as const,
    scrollbarSize: 6,
    offsetScrollbars: true,
};
