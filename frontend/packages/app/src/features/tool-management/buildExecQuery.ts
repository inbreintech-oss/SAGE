/** MCP 도구 exec query JSON — Pydantic 래퍼(request) 모델 대응 (질의어 미입력 시 fallback) */
import { isActionableExecPlaceholder } from "@/libs/stores/toolManagement/execPlaceholder";

export { isActionableExecPlaceholder };

const NESTED_UNDER_REQUEST = new Set(["stock_code", "period_code", "symbol"]);

/** POST /tool/exec — query 필드 (사용자 질의 우선, 없으면 파라미터 JSON fallback) */
export function resolveToolExecQuery(
    execQuery: string,
    execQueryPlaceholder: string,
    paramName: string,
    paramValue: string,
): string {
    if (execQuery.trim()) return execQuery.trim();
    if (isActionableExecPlaceholder(execQueryPlaceholder)) {
        return execQueryPlaceholder.trim();
    }
    return buildExecQuery(paramName, paramValue);
}

export function buildExecQuery(paramName: string, paramValue: string): string {
    const value = paramValue.trim();

    if (paramName === "request") {
        return JSON.stringify({
            request: { stock_code: value || "005930" },
        });
    }

    if (NESTED_UNDER_REQUEST.has(paramName)) {
        return JSON.stringify({ request: { [paramName]: value } });
    }

    return JSON.stringify({ [paramName]: value });
}

/** API spec: result may be JSON object or string */
export function normalizeToolExecResult(result: unknown): unknown {
    if (typeof result !== "string") return result;

    const trimmed = result.trim();
    if (!trimmed) return result;

    try {
        return JSON.parse(trimmed) as unknown;
    } catch {
        return { message: trimmed };
    }
}

/** POST /tool/exec — tools[] (메인 도구 + 선택된 토큰 도구) */
export function buildToolExecTools(toolId: string, tokenToolId?: string | null): string[] {
    const main = toolId.trim();
    const token = tokenToolId?.trim();
    if (!main) return [];
    if (token && token !== main) return [main, token];
    return [main];
}
