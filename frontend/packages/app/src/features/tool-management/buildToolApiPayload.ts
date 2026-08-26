import type { ToolFormDraft } from "@/libs/stores/toolManagement/types";
import { resolveCategoryApiSlug } from "./buildAssetPath";

export const DEFAULT_TOOL_USER_ID = "admin";

export function parseTagsFromKeyword(keyword: string): string[] {
    return keyword
        .split(",")
        .map(t => t.trim())
        .filter(Boolean);
}

/**
 * Textarea Python 코드 → API JSON body용 문자열.
 * CRLF/CR을 LF로 정규화하고 앞뒤 공백만 제거합니다.
 * HTTP 전송 시 JSON.stringify가 줄바꿈을 `\n` 이스케이프한 1라인 JSON으로 직렬화합니다.
 */
export function serializePythonCodeForJson(code: string): string {
    return code.replace(/\r\n/g, "\n").replace(/\r/g, "\n").trim();
}

/** 비어 있으면 ref_code 필드 생략 (optional 참조 코드) */
function resolveRefCodePayload(code: string): { ref_code?: string } {
    const serialized = serializePythonCodeForJson(code);
    return serialized ? { ref_code: serialized } : {};
}

/** 비어 있으면 secret_id 필드 생략 (optional) */
function resolveSecretIdPayload(secretId: string): { secret_id?: string } {
    const trimmed = secretId.trim();
    return trimmed ? { secret_id: trimmed } : {};
}

/** POST /tool/generate — Request body (Tool API v1.3) */
export function buildGenerateApiPayload(
    draft: ToolFormDraft,
    userId: string = DEFAULT_TOOL_USER_ID,
) {
    return {
        category: resolveCategoryApiSlug(draft.category),
        description: draft.description.trim(),
        query: draft.query.trim(),
        ...resolveRefCodePayload(draft.code),
        ...resolveSecretIdPayload(draft.provider),
        tags: parseTagsFromKeyword(draft.keyword),
        tools: draft.tokenToolId.trim() ? [draft.tokenToolId.trim()] : [],
        user_id: userId,
    };
}

/** POST /tool/assetize — Request body (Tool API v1.3) */
export function buildAssetizeApiPayload(
    draft: ToolFormDraft,
    toolId: string,
    assetPath: string,
) {
    return {
        asset_path: assetPath,
        title: draft.title.trim(),
        description: draft.description.trim(),
        tool_id: toolId,
    };
}

/** PATCH /tool/update — Request body (Tool API v1.3) */
export function buildUpdateApiPayload(
    draft: ToolFormDraft,
    toolId: string,
    options?: { comment?: string },
) {
    const saveQuery = draft.query.trim();
    return {
        category: resolveCategoryApiSlug(draft.category),
        comment: options?.comment ?? (draft.description.trim() || saveQuery),
        description: draft.description.trim(),
        query: saveQuery,
        ...resolveRefCodePayload(draft.code),
        ...resolveSecretIdPayload(draft.provider),
        tags: parseTagsFromKeyword(draft.keyword),
        tool_id: toolId,
        tools: draft.tokenToolId.trim() ? [draft.tokenToolId.trim()] : [],
    };
}
