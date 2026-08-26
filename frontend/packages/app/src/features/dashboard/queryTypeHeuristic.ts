import type { ReportListItem } from "@/features/report-management/reportListTypes";

/** 1차 클라이언트 휴리스틱 — 2차 API query_type 도입 시 resolveQueryType만 교체 */
export type QueryType = "short" | "exploratory" | "detailed";

export const QUERY_TYPE_LABELS: Record<QueryType, string> = {
    short: "단답형",
    exploratory: "탐색형",
    detailed: "상세분석형",
};

export function classifyQueryType(query: string | undefined | null): QueryType | null {
    const trimmed = query?.trim();
    if (!trimmed) return null;
    const len = trimmed.length;
    if (len < 50) return "short";
    if (len <= 150) return "exploratory";
    return "detailed";
}

/** 2차: report.query_type 등 API 필드 우선 */
export function resolveQueryType(report: ReportListItem): QueryType | null {
    return classifyQueryType(report.query);
}
