import type { ReportBlockData, ReportBlockRole, ReportBlockType, ReportLayoutBlock } from "./reportDocumentTypes";

export const SEMANTIC_BLOCK_TYPES = new Set<string>([
    "document_title",
    "section_title",
    "summary_card",
    "insight_card",
    "kpi_card",
    "text_card",
    "closing_card",
    "metrics_table",
    "appendix_table",
    "primary_chart",
    "secondary_chart",
]);

const KNOWN_ROLES = new Set<string>([
    "report_title",
    "section_header",
    "executive_summary",
    "kpi_row",
    "key_findings",
    "chart_insight",
    "table_insight",
    "conclusions",
    "methodology",
    "metrics_table",
    "appendix_table",
    "primary_chart",
    "secondary_chart",
]);

const TYPE_DEFAULT_ROLE: Record<string, ReportBlockRole> = {
    document_title: "report_title",
    section_title: "section_header",
    summary_card: "executive_summary",
    insight_card: "chart_insight",
    kpi_card: "kpi_row",
    text_card: "methodology",
    closing_card: "conclusions",
    metrics_table: "metrics_table",
    appendix_table: "appendix_table",
    primary_chart: "primary_chart",
    secondary_chart: "secondary_chart",
    header: "report_title",
    card: "key_findings",
    echart: "primary_chart",
    chart: "primary_chart",
    table: "metrics_table",
};

export function isKnownRole(role: string | undefined): role is ReportBlockRole {
    return Boolean(role && KNOWN_ROLES.has(role));
}

export function resolvePayloadRole(
    payload: ReportBlockData | undefined,
    blockType: ReportBlockType,
    layoutRole?: ReportBlockRole,
): ReportBlockRole | undefined {
    if (payload && typeof payload === "object" && "role" in payload) {
        const r = (payload as { role?: string }).role;
        if (isKnownRole(r)) return r;
    }
    if (isKnownRole(layoutRole)) return layoutRole;
    const def = TYPE_DEFAULT_ROLE[blockType];
    return isKnownRole(def) ? def : undefined;
}

export function resolveHeaderType(
    blockType: ReportBlockType,
    payload: ReportBlockData | undefined,
): "document_title" | "section_title" | "header" {
    if (blockType === "document_title" || blockType === "section_title") return blockType;
    if (blockType !== "header") return "header";
    const level = payload && typeof payload === "object" && "level" in payload
        ? Number((payload as { level?: number }).level)
        : 1;
    return level >= 2 ? "section_title" : "document_title";
}

export function isCardBlockType(type: ReportBlockType): boolean {
    return type === "card"
        || type === "summary_card"
        || type === "insight_card"
        || type === "kpi_card"
        || type === "text_card"
        || type === "closing_card";
}

export function isChartBlockType(type: ReportBlockType): boolean {
    return type === "echart"
        || type === "chart"
        || type === "primary_chart"
        || type === "secondary_chart";
}

export function isTableBlockType(type: ReportBlockType): boolean {
    return type === "table" || type === "metrics_table" || type === "appendix_table";
}

export function isLayoutContainer(block: ReportLayoutBlock): boolean {
    return block.type === "rows" || block.type === "cols";
}
