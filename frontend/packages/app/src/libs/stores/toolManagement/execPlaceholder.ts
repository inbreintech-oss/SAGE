const GENERIC_EXEC_PLACEHOLDER_MARKERS = [
    "실행용 테스트 질의어를 입력하거나",
    "새 도구를 생성하면",
    "추천 질의문을 불러오는",
] as const;

export function isActionableExecPlaceholder(placeholder?: string | null): boolean {
    const text = placeholder?.trim();
    if (!text) return false;
    return !GENERIC_EXEC_PLACEHOLDER_MARKERS.some(marker => text.includes(marker));
}
