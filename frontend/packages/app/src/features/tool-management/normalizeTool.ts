import type { Tool, ToolApiStatus } from "@/features/tool/api";
import { coerceQueryExamples } from "@/features/tool-management/resolveQueryExamples";
import type { ToolAssetStatus, ToolListItem } from "@/libs/stores/toolManagement/types";
import {
    DEFAULT_CATEGORY_CODE,
    resolveCategoryCode,
    type CategoryCode,
} from "@/libs/stores/toolManagement/commonCodes";

function hashToolId(toolId: string): number {
    let hash = 0;
    for (let i = 0; i < toolId.length; i++) {
        hash = ((hash << 5) - hash) + toolId.charCodeAt(i);
        hash |= 0;
    }
    return Math.abs(hash);
}

const CATEGORY_KEYWORD_POOLS: Record<CategoryCode, string[]> = {
    CAT_STOCK: ["주식", "시세", "한국투자증권", "코스피"],
    CAT_REALESTATE: ["부동산", "실거래가", "아파트", "국토교통부"],
    CAT_IP: ["특허", "상표권", "KIPRIS", "지식재산"],
    CAT_WEATHER: ["날씨", "기상", "온도", "예보"],
    CAT_FINANCE: ["금융", "분석", "API", "데이터"],
    CAT_STATISTICS: ["통계", "분석", "집계", "데이터"],
};

const FALLBACK_KEYWORD_POOL = ["API", "데이터", "조회", "분석"];

function pickPlaceholderKeywords(toolId: string, categoryCode: CategoryCode): string[] {
    const pool = CATEGORY_KEYWORD_POOLS[categoryCode] ?? FALLBACK_KEYWORD_POOL;
    const seed = hashToolId(toolId);
    const count = 3 + (seed % 2);
    const indices = new Set<number>();

    for (let i = 0; i < pool.length && indices.size < count; i++) {
        const idx = (seed + i * 7) % pool.length;
        indices.add(idx);
    }

    return Array.from(indices).map(i => pool[i]);
}

function resolveKeyword(tool: Tool, categoryCode: CategoryCode): string {
    const fromTags = (tool.tags ?? []).map(t => t.trim()).filter(Boolean);
    if (fromTags.length > 0) {
        return fromTags.join(", ");
    }
    return pickPlaceholderKeywords(tool.tool_id, categoryCode).join(", ");
}

function resolveQueryExample(tool: Tool): string {
    return coerceQueryExamples(tool.query_examples)?.[0] ?? "";
}

function mapApiStatusToUiStatus(status: ToolApiStatus): ToolAssetStatus {
    return status === "assetized" ? "assetized" : "generated";
}

/** 목록 카드 표시용 키워드 */
export function resolveDisplayKeywords(tool: ToolListItem): string[] {
    const fromField = String(tool.keyword ?? "")
        .split(",")
        .map(k => k.trim())
        .filter(Boolean);

    if (fromField.length > 0) return fromField;
    return pickPlaceholderKeywords(tool.tool_id, resolveCategoryCode(tool.category));
}

/** 목록 재조회 시 API secret_id 누락 — 기존 목록 캐시 provider/tokenToolId 보존 */
export function mergeToolListItemFromCache(
    item: ToolListItem,
    previous?: ToolListItem,
): ToolListItem {
    if (!previous) return item;

    return {
        ...item,
        provider: item.provider.trim() || previous.provider,
        tokenToolId: item.tokenToolId?.trim() || previous.tokenToolId,
        query: item.query.trim() || previous.query,
    };
}

export function normalizeToolItem(tool: Tool): ToolListItem {
    const fromCode = parseDefaultParamsFromCode(tool.code);
    const fromCaller = parseDefaultParamsFromCaller(tool.caller);
    const defaultParams = Object.keys({ ...fromCode, ...fromCaller }).length > 0
        ? { ...fromCode, ...fromCaller }
        : { parameter: "" };

    const categoryCode = resolveCategoryCode(tool.category?.trim() || inferCategoryCode(tool));
    const queryExample = resolveQueryExample(tool);
    const secretId = tool.secret_id?.trim() || tool.provider?.trim() || "";

    return {
        tool_id: tool.tool_id,
        title: tool.title,
        description: tool.description ?? "",
        category: categoryCode,
        keyword: resolveKeyword(tool, categoryCode),
        query: queryExample,
        code: tool.code ?? "",
        default_parameters: defaultParams,
        status: mapApiStatusToUiStatus(tool.status),
        apiStatus: tool.status,
        provider: secretId,
        recommendationQuery: queryExample || `${tool.title} 도구를 활용한 자연어 미리보기 정합성 검증을 시동해줘.`,
        created_at: tool.created_at,
        updated_at: tool.updated_at,
    };
}

function inferCategoryCode(tool: Tool): CategoryCode {
    const title = `${tool.title} ${tool.description} ${tool.category ?? ""}`.toLowerCase();
    if (title.includes("주식") || title.includes("stock")) return "CAT_STOCK";
    if (title.includes("부동산") || title.includes("real")) return "CAT_REALESTATE";
    if (title.includes("특허") || title.includes("patent") || title.includes("상표") || title.includes("trademark")) {
        return "CAT_IP";
    }
    if (title.includes("날씨") || title.includes("weather")) return "CAT_WEATHER";
    if (title.includes("finance") || title.includes("금융")) return "CAT_FINANCE";
    if (title.includes("통계") || title.includes("statistic")) return "CAT_STATISTICS";
    return DEFAULT_CATEGORY_CODE;
}

/** caller 스크립트에서 첫 번째 파라미터 힌트 추출 */
export function parseDefaultParamsFromCaller(caller?: string | null): Record<string, string> {
    if (!caller) return { parameter: "" };

    const quotedStock = caller.match(/"stock_code"\s*:\s*"([^"]+)"/);
    if (quotedStock?.[1]) {
        return { stock_code: quotedStock[1].trim() };
    }

    const assignStock = caller.match(/stock_code\s*=\s*["']([^"']+)["']/);
    if (assignStock?.[1]) {
        return { stock_code: assignStock[1].trim() };
    }

    const unquotedStock = caller.match(/"stock_code"\s*:\s*([A-Za-z_]\w*)/);
    if (unquotedStock?.[1] && unquotedStock[1] !== "stock_code") {
        return { stock_code: unquotedStock[1].trim() };
    }

    const genericQuoted = caller.match(/"(\w+)"\s*:\s*"([^"]+)"/);
    if (genericQuoted?.[1] && genericQuoted[2]) {
        return { [genericQuoted[1]]: genericQuoted[2].trim() };
    }

    const genericAssign = caller.match(/(\w+)\s*=\s*["']([^"']+)["']/);
    if (genericAssign?.[1] && genericAssign[2]) {
        return { [genericAssign[1]]: genericAssign[2].trim() };
    }

    return { parameter: "" };
}

const STOCK_CODE_FALLBACK = "005930";

export function parseDefaultParamsFromCode(code?: string): Record<string, string> {
    if (!code) return {};

    const fieldExample = code.match(
        /stock_code[\s\S]*?description\s*=\s*["'][^"']*['"](\d{6})['"]/,
    );
    if (fieldExample?.[1]) {
        return { stock_code: fieldExample[1] };
    }

    const assignInCode = code.match(/stock_code\s*=\s*["'](\d{6})["']/);
    if (assignInCode?.[1]) {
        return { stock_code: assignInCode[1] };
    }

    return {};
}

export function resolveExecPreview(
    caller?: string,
    funcInputs?: { name: string; properties?: { name: string }[] }[],
    code?: string,
): { paramName: string; paramValue: string } {
    const fromCaller = parseDefaultParamsFromCaller(caller);
    const fromCode = parseDefaultParamsFromCode(code);
    const merged = { ...fromCode, ...fromCaller };
    const callerEntry = Object.entries(merged)[0] ?? ["parameter", ""];

    const resolveValue = (name: string, fallback = ""): string => {
        const v = merged[name] ?? callerEntry[1] ?? fallback;
        if (v && v !== name) return v;
        if (name === "stock_code") return STOCK_CODE_FALLBACK;
        return fallback;
    };

    if (funcInputs && funcInputs.length > 0) {
        const root = funcInputs[0];

        if (root.name === "request" && root.properties?.length) {
            const innerName = root.properties[0].name;
            return {
                paramName: innerName,
                paramValue: resolveValue(innerName, STOCK_CODE_FALLBACK),
            };
        }

        return {
            paramName: root.name,
            paramValue: resolveValue(root.name),
        };
    }

    if (merged.stock_code || callerEntry[0] === "stock_code") {
        return {
            paramName: "stock_code",
            paramValue: resolveValue("stock_code", STOCK_CODE_FALLBACK),
        };
    }

    return {
        paramName: callerEntry[0],
        paramValue: resolveValue(callerEntry[0]),
    };
}
