/** UI·API 공통 코드 — Single Source of Truth (향후 공통코드 관리 연동) */
export const COMMON_CODES = {
    CATEGORIES: [
        { label: "부동산", code: "CAT_REALESTATE" },
        { label: "주식", code: "CAT_STOCK" },
        { label: "특허/상표권", code: "CAT_IP" },
        { label: "날씨", code: "CAT_WEATHER" },
        { label: "금융", code: "CAT_FINANCE" },
        { label: "통계", code: "CAT_STATISTICS" },
    ],
    PROVIDERS: [
        { label: "한국투자증권 (KIS)", code: "PROV_KIS" },
        { label: "국토교통부 (MOLIT)", code: "PROV_MOLIT" },
        { label: "특허정보진흥원 (KIPRIS)", code: "PROV_KIPRIS" },
        { label: "날씨 (WEATHER)", code: "PROV_WEATHER" },
        { label: "금융 (FINANCE)", code: "PROV_FINANCE" },
    ],
} as const;

export type CategoryCode = (typeof COMMON_CODES.CATEGORIES)[number]["code"];
export type ProviderCode = (typeof COMMON_CODES.PROVIDERS)[number]["code"];

export const DEFAULT_CATEGORY_CODE: CategoryCode = "CAT_REALESTATE";

const CATEGORY_CODE_SET = new Set<string>(COMMON_CODES.CATEGORIES.map(c => c.code));
const PROVIDER_CODE_SET = new Set<string>(COMMON_CODES.PROVIDERS.map(p => p.code));

/** Select 옵션 — Category */
export function populateCategoryOptions() {
    return COMMON_CODES.CATEGORIES.map(c => ({ value: c.code, label: c.label }));
}

/** Select 옵션 — Provider */
export function populateProviderOptions() {
    return COMMON_CODES.PROVIDERS.map(p => ({ value: p.code, label: p.label }));
}

export function getCategoryLabel(code: string): string {
    return COMMON_CODES.CATEGORIES.find(c => c.code === code)?.label ?? code;
}

export function getProviderLabel(code: string): string {
    return COMMON_CODES.PROVIDERS.find(p => p.code === code)?.label ?? code;
}

const LEGACY_CATEGORY_TO_CODE: Record<string, CategoryCode> = {
    "부동산": "CAT_REALESTATE",
    "주식": "CAT_STOCK",
    "특허": "CAT_IP",
    "상표권": "CAT_IP",
    "특허/상표권": "CAT_IP",
    "날씨": "CAT_WEATHER",
    "금융": "CAT_FINANCE",
    "통계": "CAT_STATISTICS",
    finance: "CAT_FINANCE",
    statistics: "CAT_STATISTICS",
    stats: "CAT_STATISTICS",
    stock: "CAT_STOCK",
    "real-estate": "CAT_REALESTATE",
    patent: "CAT_IP",
    trademark: "CAT_IP",
    weather: "CAT_WEATHER",
};

const LEGACY_PROVIDER_TO_CODE: Record<string, ProviderCode> = {
    KIS: "PROV_KIS",
    MOLIT: "PROV_MOLIT",
    KIPRIS: "PROV_KIPRIS",
    KIPO: "PROV_KIPRIS",
    KMA: "PROV_WEATHER",
    kis: "PROV_KIS",
    molit: "PROV_MOLIT",
    kipris: "PROV_KIPRIS",
    weather: "PROV_WEATHER",
    finance: "PROV_FINANCE",
    "한투": "PROV_KIS",
    "한국투자증권": "PROV_KIS",
};

/** API·레거시 응답 → 공통 category code */
export function resolveCategoryCode(raw: string | null | undefined): CategoryCode {
    const trimmed = raw?.trim();
    if (!trimmed) return DEFAULT_CATEGORY_CODE;
    if (CATEGORY_CODE_SET.has(trimmed)) return trimmed as CategoryCode;
    const byLabel = COMMON_CODES.CATEGORIES.find(c => c.label === trimmed);
    if (byLabel) return byLabel.code;
    return LEGACY_CATEGORY_TO_CODE[trimmed] ?? DEFAULT_CATEGORY_CODE;
}

/** API·레거시 응답 → 공통 provider code */
export function resolveProviderCode(
    raw: string | null | undefined,
    fallback: ProviderCode = "PROV_KIS",
): ProviderCode {
    const trimmed = raw?.trim();
    if (!trimmed) return fallback;
    if (PROVIDER_CODE_SET.has(trimmed)) return trimmed as ProviderCode;
    const byLabel = COMMON_CODES.PROVIDERS.find(p => p.label === trimmed);
    if (byLabel) return byLabel.code;
    return LEGACY_PROVIDER_TO_CODE[trimmed] ?? fallback;
}
