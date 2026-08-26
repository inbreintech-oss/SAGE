export { COMMON_CODES, DEFAULT_CATEGORY_CODE, populateCategoryOptions, populateProviderOptions, getCategoryLabel, getProviderLabel, resolveCategoryCode, resolveProviderCode } from "./commonCodes";
export type { CategoryCode, ProviderCode } from "./commonCodes";

export const DEFAULT_NEW_TOOL_CODE = `def custom_analytic_tool(parameter: str) -> dict:
    """
    여기에 SAGE 엔진이 분석할 신규 도구의 Python 코드를 작성하세요.
    """
    import pandas as pd

    # 내부 인메모리 스키마 연산
    return {"status": "SUCCESS"}`;

export const SCHEMA_ALREADY_EXISTS_MESSAGE =
    "이미 생성된 통합 도구 스키마가 있으므로 생성이 제한됩니다.";

export const ALREADY_SAVED_MESSAGE =
    "이미 생성된 도구입니다. [도구수정]을 진행하거나 [도구저장]으로 자산화해 주세요.";

export const DUPLICATE_TITLE_MESSAGE =
    "정보가 변경되었습니다. 기존 도구와 구별하기 위해 고유한 도구명을 새로 수정해 주세요.";

export const EXEC_NO_SAVE_POINT_MESSAGE =
    "미리보기를 실행하려면 [도구생성]을 완료하거나, 등록된 도구를 선택해 주세요.";

/** 조회 성공 · 결과 0건 */
export const EMPTY_LIST_MESSAGE = "등록된 도구(API)가 없습니다.";

/** 조회 실패 — UI 표시용 (기술 상세는 콘솔 로그) */
export const LIST_LOAD_ERROR_MESSAGE =
    "도구 목록을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.";

/** 좌측 목록 조회 대상 없음 — 아이콘·문구 색상 (ToolManagement) */
export const LIST_EMPTY_STATE_COLOR = "#1C7ED6";

export const SEARCH_PLACEHOLDER = "도구명, 카테고리, 키워드로 검색...";

export const UNSELECTED_JSON_PREVIEW =
    "// 실시간 API 호출 및 트랜잭션 로그 콘솔 대기 중...";

export const INITIAL_TRACE_LOGS = [
    "[SYSTEM] SAGE Analytics API Gateway Host Initialized.",
    "[SYSTEM] Listening on loopback port 5001.",
    ">_ Waiting for test trigger or asset registration...",
] as const;

export const UNSELECTED_TRACE_LOGS = [
    ">_ // 실시간 API 호출 및 트랜잭션 로그 콘솔 대기 중...",
] as const;

export const NEW_TOOL_JSON_PREVIEW = "// 대기 중: 도구 생성 진행 상황 로그가 실시간 노출됩니다.";

export function buildSelectedToolJsonPreview(toolTitle: string): string {
    return `// [${toolTitle}] 도구 미리보기 실행을\n// 클릭하시면 내부 보안망 연산 결과가\n// 이곳에 실시간 노출됩니다.`;
}

export const VISUAL_EXEC_GUIDE_DESC =
    "하단의 '미리보기 실행' 버튼을 클릭하면, 내부 실행 환경에서 산출된 분석 통계 알고리즘 수식 및 최종 데이터셋 결과가 정교하게 렌더링됩니다.";

export const VISUAL_SELECT_GUIDE_DESC =
    "좌측 목록에서 편집하거나 실행할 도구(API)를 선택해 주세요.";
