import type { ToolApiStatus } from "@/features/tool/api";

type GenerateResultLike = {
    tool_id?: string;
    title?: string;
    description?: string;
    code?: string;
    caller?: string;
    query_examples?: unknown;
    category?: string;
    tags?: string[];
    secret_id?: string;
    status?: ToolApiStatus;
    created_at?: string;
    updated_at?: string;
};

/** generate/update SSE·REST — result 배열·래퍼·단일 객체에서 tool_id 추출 */
export function resolveToolIdFromGeneratePayload(raw: unknown): string | undefined {
    const resolved = resolveGenerateResult(raw);
    return resolved?.tool_id?.trim() || undefined;
}

/** string | string[] | null → string[] */
export function coerceQueryExamples(raw: unknown): string[] | null {
    if (raw == null) return null;

    if (Array.isArray(raw)) {
        const normalized = raw
            .map(item => String(item).trim())
            .filter(Boolean);
        return normalized.length > 0 ? normalized : null;
    }

    if (typeof raw === "string" && raw.trim()) {
        return [raw.trim()];
    }

    return null;
}

/** generate SSE completed.result — v1.3 result[] · 단일 객체 · { result: [] } 래퍼 수용 */
export function resolveGenerateResult(raw: unknown): GenerateResultLike | undefined {
    if (!raw) return undefined;

    if (typeof raw === "string") return undefined;

    if (typeof raw !== "object") return undefined;

    const wrapped = raw as { result?: unknown; success?: boolean };
    if (Array.isArray(wrapped.result)) {
        const first = wrapped.result[0];
        return first && typeof first === "object" ? (first as GenerateResultLike) : undefined;
    }

    if (Array.isArray(raw)) {
        const first = raw[0];
        return first && typeof first === "object" ? (first as GenerateResultLike) : undefined;
    }

    return raw as GenerateResultLike;
}

/** SSE completed·list item 등 — query_examples를 여러 경로에서 수집 */
export function collectQueryExamplesFromPayload(payload: unknown): string[] | null {
    if (!payload || typeof payload !== "object") return null;

    const obj = payload as Record<string, unknown>;
    const topLevel = coerceQueryExamples(obj.query_examples);
    if (topLevel?.length) return topLevel;

    const resolved = resolveGenerateResult(obj.result ?? obj);
    const fromResolved = coerceQueryExamples(resolved?.query_examples);
    if (fromResolved?.length) return fromResolved;

    if (Array.isArray(obj.result)) {
        for (const item of obj.result) {
            if (!item || typeof item !== "object") continue;
            const nested = coerceQueryExamples((item as Record<string, unknown>).query_examples);
            if (nested?.length) return nested;
        }
    }

    return null;
}

/** list/query·generate 공통 — query_examples 또는 query 문자열에서 실행 질의 추출 */
export function resolveExecQueryText(
    queryExamples?: string[] | null,
    queryFallback?: string | null,
    titleFallback?: string,
    recommendationFallback?: string | null,
): string | undefined {
    const fromExamples = pickExecQueryPlaceholder(queryExamples);
    if (fromExamples) return fromExamples;

    const fromRecommendation = recommendationFallback?.trim();
    if (fromRecommendation) return fromRecommendation;

    const fromQuery = queryFallback?.trim();
    if (fromQuery) return fromQuery;

    if (titleFallback?.trim()) {
        return `${titleFallback.trim()} 도구를 활용한 자연어 미리보기 정합성 검증을 시동해줘.`;
    }

    return undefined;
}

/** query_examples → 실행용 테스트 질의어 (첫 번째 예시) */
export function pickExecQueryPlaceholder(examples?: string[] | null): string | undefined {
    const normalized = coerceQueryExamples(examples);
    return normalized?.[0];
}
