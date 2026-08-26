import type { Tool, ToolApiStatus } from "@/features/tool/api";

/** 연계기관 인증 토큰 도구 조회 — status OR (assetized | generated) */
export const TOKEN_TOOL_LIST_STATUSES: readonly ToolApiStatus[] = [
    "assetized",
    "generated",
] as const;

/** 토큰 도구 tags OR 매칭 키워드 — 도구 tags 중 하나라도 포함되면 후보 */
export const TOKEN_TOOL_TAGS = ["token", "토큰", "인증", "auth", "authorization"] as const;

function normalizeTag(value: string): string {
    return value.trim().toLowerCase();
}

/** 연계기관 인증 토큰 도구 — secret_id 일치 + status OR + tags OR */
export function matchesTokenToolFilter(
    tool: Tool,
    secretId: string,
    statuses: readonly ToolApiStatus[] = TOKEN_TOOL_LIST_STATUSES,
    tagKeywords: readonly string[] = TOKEN_TOOL_TAGS,
): boolean {
    const trimmedSecret = secretId.trim();
    if (!trimmedSecret) return false;

    const toolSecret = tool.secret_id?.trim() || tool.provider?.trim() || "";
    if (toolSecret !== trimmedSecret) return false;

    if (!statuses.includes(tool.status)) return false;

    const keywordSet = new Set(tagKeywords.map(normalizeTag));
    const toolTags = (tool.tags ?? []).map(normalizeTag).filter(Boolean);
    return toolTags.some(tag => keywordSet.has(tag));
}

export function filterTokenTools(
    tools: Tool[],
    secretId: string,
): Tool[] {
    return tools.filter(tool => matchesTokenToolFilter(tool, secretId));
}
