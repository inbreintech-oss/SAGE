import type { ToolFormDraft } from "./types";

const EDITABLE_KEYS = [
    "title",
    "description",
    "category",
    "keyword",
    "query",
    "code",
    "provider",
    "tokenToolId",
] as const;

export function normalizeDraftFields(draft: ToolFormDraft) {
    return {
        title: draft.title.trim(),
        description: draft.description.trim(),
        category: draft.category.trim(),
        keyword: draft.keyword.trim(),
        query: draft.query.trim(),
        code: draft.code.trim(),
        provider: draft.provider.trim(),
        tokenToolId: draft.tokenToolId.trim(),
    };
}

export function draftsAreEqual(a: ToolFormDraft, b: ToolFormDraft): boolean {
    const na = normalizeDraftFields(a);
    const nb = normalizeDraftFields(b);
    return EDITABLE_KEYS.every(key => na[key] === nb[key]);
}
