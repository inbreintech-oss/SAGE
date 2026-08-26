export const TOKEN_TOOL_FIELD_LABEL = "연계기관 인증 토큰 도구";

export const TOKEN_TOOL_EMPTY_HINT =
    "연계 API 호출 시 인증 토큰이 필요할 수 있습니다. 미리보기 실행 전「연계기관 인증 토큰 도구」를 선택해 주세요.";

export const TOKEN_EXEC_ERROR_GUIDE =
    "API 인증·토큰 관련 오류로 보입니다. 상단「연계기관 인증 토큰 도구」를 선택한 뒤 도구를 다시 생성·저장하고 미리보기를 실행해 주세요.";

const TOKEN_ERROR_PATTERNS = [
    "token",
    "토큰",
    "auth",
    "인증",
    "unauthorized",
    "401",
    "403",
    "secret",
    "appkey",
    "appsecret",
    "access_token",
    "bearer",
    "만료",
    "expired",
];

export function isLikelyTokenAuthError(message: string): boolean {
    const lower = message.toLowerCase();
    return TOKEN_ERROR_PATTERNS.some(p => lower.includes(p.toLowerCase()));
}

export function buildTokenExecErrorMessage(
    rawError: string,
    hasTokenToolSelected: boolean,
): string {
    if (hasTokenToolSelected || !isLikelyTokenAuthError(rawError)) {
        return rawError;
    }
    return `${rawError}\n\n${TOKEN_EXEC_ERROR_GUIDE}`;
}
