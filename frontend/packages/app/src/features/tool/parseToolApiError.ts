type ValidationDetailItem = {
    loc?: (string | number)[];
    msg?: string;
    type?: string;
    input?: unknown;
};

type ToolApiErrorBody = {
    error?: string | null;
    detail?: string | ValidationDetailItem[];
    msg?: string;
    message?: string;
};

const FIELD_LABELS: Record<string, string> = {
    body: "요청",
    category: "도구 카테고리",
    provider: "API 연계 기관",
    secret_id: "API 연계 기관",
    ref_code: "예시 코드",
    code: "예시 코드",
    description: "도구설명",
    query: "질의문",
    tags: "연관 키워드",
    tools: "참조 도구",
    user_id: "사용자",
    tool_id: "도구 ID",
    title: "도구명",
    comment: "수정 코멘트",
};

function resolveFieldLabel(loc: (string | number)[] | undefined): string {
    const key = loc?.find(part => typeof part === "string") as string | undefined;
    if (key && FIELD_LABELS[key]) return FIELD_LABELS[key];
    return "입력값";
}

function formatValidationDetails(detail: ValidationDetailItem[]): string {
    return detail
        .map(item => {
            const field = item.loc?.filter(part => typeof part === "string").join(".") ?? "field";
            const msg = item.msg ?? "유효하지 않은 값입니다.";
            return `${field}: ${msg}`;
        })
        .join("\n");
}

/** Toast/UI용 — 시스템 loc 노출 최소화 */
function formatValidationDetailsForToast(detail: ValidationDetailItem[]): string {
    return detail
        .map(item => {
            const label = resolveFieldLabel(item.loc);
            const msg = item.msg ?? "값을 확인해 주세요.";
            return `${label}: ${msg}`;
        })
        .join("\n");
}

/** FastAPI Validation Error(detail[]) 및 공통 error 필드 파싱 */
export function parseToolApiError(data: unknown, fallback = "요청 처리 중 오류가 발생했습니다."): string {
    if (!data || typeof data !== "object") {
        return fallback;
    }

    const body = data as ToolApiErrorBody;

    if (Array.isArray(body.detail) && body.detail.length > 0) {
        return formatValidationDetails(body.detail);
    }

    if (typeof body.detail === "string" && body.detail.trim()) {
        return body.detail;
    }

    if (body.error && String(body.error).trim()) {
        return String(body.error);
    }

    if (body.message && String(body.message).trim()) {
        return String(body.message);
    }

    if (body.msg && String(body.msg).trim()) {
        return String(body.msg);
    }

    return fallback;
}

/** Toast 알림용 Validation Error 메시지 */
export function parseToolApiErrorForToast(data: unknown, fallback = "요청 처리 중 오류가 발생했습니다."): string {
    if (!data || typeof data !== "object") {
        return fallback;
    }

    const body = data as ToolApiErrorBody;

    if (Array.isArray(body.detail) && body.detail.length > 0) {
        return formatValidationDetailsForToast(body.detail);
    }

    return parseToolApiError(data, fallback);
}

