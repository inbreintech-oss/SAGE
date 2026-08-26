import type { ToolFormDraft } from "@/libs/stores/toolManagement/types";
import { buildGenerateApiPayload } from "./buildToolApiPayload";

/** @deprecated 신규 명세는 query·code 분리 — draft.query 직접 사용 권장 */
export function buildGenerateQuery(draft: ToolFormDraft): string {
    const query = draft.query.trim();
    const code = draft.code.trim();
    if (query && code) return `${query}\n${code}`;
    return query || code;
}

/** POST /tool/generate 요청 body */
export function buildGeneratePayload(draft: ToolFormDraft) {
    return buildGenerateApiPayload(draft);
}
