import type { Tool, ToolApiStatus } from "@/features/tool/api";

/** 도구 관리 좌측 목록 — assetized + generated (syntax-passed·보고서 status 제외) */
export const TOOL_MANAGEMENT_LIST_STATUSES: readonly ToolApiStatus[] = [
    "assetized",
    "generated",
] as const;

const REPORT_API_STATUSES = new Set(["completed", "published", "initializing"]);

type ToolListRecord = Tool & {
    rid?: string;
    plan_id?: string;
    did?: string;
};

/** /tool/list/query 혼입 가능한 보고서 레코드 식별 */
export function isReportLikeToolRecord(tool: ToolListRecord): boolean {
    if (tool.rid?.trim()) return true;
    if (tool.plan_id?.trim() && !tool.code?.trim()) return true;

    const status = String(tool.status ?? "").toLowerCase();
    if (REPORT_API_STATUSES.has(status)) return true;

    const tags = (tool.tags ?? []).map(t => t.trim().toLowerCase());
    if (tags.some(t => t === "report" || t === "보고서")) return true;

    const toolId = tool.tool_id?.trim() ?? "";
    if (/^rid[-_]/i.test(toolId)) return true;

    return false;
}

/** 도구(API) 관리 좌측 목록 — API 도구만 노출 */
export function filterToolsForManagementList(tools: Tool[]): Tool[] {
    return tools.filter(
        t => TOOL_MANAGEMENT_LIST_STATUSES.includes(t.status)
            && !isReportLikeToolRecord(t),
    );
}
