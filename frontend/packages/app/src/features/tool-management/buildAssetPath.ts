const CATEGORY_CODE_SLUG: Record<string, string> = {
    CAT_STOCK: "stock",
    CAT_REALESTATE: "real-estate",
    CAT_IP: "ip",
    CAT_WEATHER: "weather",
    CAT_FINANCE: "finance",
    CAT_STATISTICS: "statistics",
};

/** Tool API v1.3 — UI category code → API category slug (예: CAT_FINANCE → finance) */
export function resolveCategoryApiSlug(categoryCode: string): string {
    const trimmed = categoryCode.trim();
    return CATEGORY_CODE_SLUG[trimmed] ?? trimmed.toLowerCase();
}

/** assetize 요청용 asset_path — tool_id 와 동일 (Tool API v1.3) */
export function buildAssetPath(toolId: string): string {
    return toolId.trim();
}
