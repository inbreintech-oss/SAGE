import type { SageData } from "@/features/data";

/**
 * 기등록 모델의 통합 스키마 존재 여부 판정 (Read vs Integrate UI 분기).
 * 1. has_schema (추후 list/detail API)
 * 2. pangea 배열 존재 (List Data v1.2)
 * 3. status === "completed" | "ready" (현재)
 */
export function resolveHasActiveSchema(item: SageData): boolean {
    if (typeof item.has_schema === "boolean") {
        return item.has_schema;
    }
    if (Array.isArray(item.pangea) && item.pangea.length > 0) {
        return true;
    }
    return item.status === "completed" || item.status === "ready";
}
