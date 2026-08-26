import {
    DEFAULT_CATEGORY_CODE,
    populateCategoryOptions,
    type CategoryCode,
} from "@/libs/stores/toolManagement/commonCodes";

/** 좌측 목록 조회 대상 없음 — 문구·색상 규격 (DataManagement) */
export const EMPTY_LIST_MESSAGE = "데이터 분석 모델 목록을 불러오지 못했습니다";

export const LIST_EMPTY_STATE_COLOR = "#1C7ED6";

export const SEARCH_PLACEHOLDER = "분석모델 검색...";

/** 데이터 등록(2) — 도구 관리와 동일 공통 카테고리 코드 */
export const DATA_CATEGORY_OPTIONS = populateCategoryOptions();

export type DataCategoryValue = CategoryCode;

export const DEFAULT_DATA_CATEGORY: DataCategoryValue = DEFAULT_CATEGORY_CODE;

export const SCHEMA_EMPTY_PLACEHOLDER =
    "통합 스키마를 생성하면 이 영역에 매핑 결과가 표시됩니다.";

export const MODEL_INFO_EMPTY_HINT =
    "선택한 모델의 스키마 정보가 아직 없습니다. 하단에서 통합 스키마를 생성해 주세요.";

/**
 * Read(모델 저장) — UI 노출 여부.
 * POST /data/save 스펙 반영 후 true 로 전환한다.
 */
export const DATA_MODEL_SAVE_UI_ENABLED = false;

/**
 * Read(모델 저장) — API 호출 여부.
 * POST /data/save 구현·배포 후 true 로 전환한다.
 */
export const DATA_MODEL_SAVE_API_ENABLED = false;

export const SAVE_MODEL_NOT_AVAILABLE_MESSAGE =
    "모델 저장 기능은 API 스펙 업데이트 후 제공됩니다.";

/**
 * 등록 유형 탭 — DB (SQL) 노출 여부.
 * DB 유형 데이터 모델 생성 로직 미구현 · 시연용으로 false.
 * 구현 완료 후 true 로 전환한다.
 */
export const DATA_SOURCE_DB_TAB_ENABLED = false;

/** Pool 원천 에셋 목록 — 타이틀 최대 표시 줄 수 (CSS line-clamp) */
export const POOL_LIST_TITLE_MAX_LINES = 4;

/** 연산 결과 JSON ScrollArea 높이(px) */
export const JSON_CONSOLE_HEIGHT_DEFAULT = 280;
export const JSON_CONSOLE_HEIGHT_STREAMING = 420;
/** 자동 tail-follow 판정 여백(px) */
export const JSON_CONSOLE_FOLLOW_THRESHOLD_PX = 48;

/** Pool 패널 안내 — DB 탭 비노출 시 파일·도구만 안내 */
export const POOL_SOURCE_BINDING_HINT = DATA_SOURCE_DB_TAB_ENABLED
    ? "등록 유형 탭에서 선택한 원천 에셋을 Pool에 적재한 뒤 통합 스키마를 생성합니다."
    : "파일 또는 도구 탭에서 선택한 원천 에셋을 Pool에 적재한 뒤 통합 스키마를 생성합니다.";
