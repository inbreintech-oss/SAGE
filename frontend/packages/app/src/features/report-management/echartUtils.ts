import type { EChartsOption } from "echarts-for-react";
import type { ReportBlockData } from "./reportDocumentTypes";

function isPlainObject(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null && !Array.isArray(value);
}

function looksLikeEchartOption(value: Record<string, unknown>): boolean {
    return "series" in value
        || "xAxis" in value
        || "yAxis" in value
        || "radar" in value
        || "geo" in value
        || "dataset" in value
        || "visualMap" in value;
}

const ECHART_META_KEYS = new Set([
    "role",
    "description",
    "insight",
    "subtitle",
    "card_type",
    "content",
    "content_type",
]);

function stripEchartMetaFields(option: Record<string, unknown>): EChartsOption {
    const out: Record<string, unknown> = {};
    for (const [key, val] of Object.entries(option)) {
        if (!ECHART_META_KEYS.has(key)) {
            out[key] = val;
        }
    }
    return out as EChartsOption;
}

const CHART_THEME_PRESETS: Record<string, Partial<EChartsOption>> = {
    "analytical-standard": {
        color: ["#2563EB", "#7C3AED", "#059669", "#D97706", "#DC2626"],
        grid: { left: 56, right: 32, bottom: 56, top: 40, containLabel: true },
        textStyle: { fontFamily: "'Noto Sans KR', sans-serif", fontSize: 11 },
        tooltip: { trigger: "axis", confine: true },
        legend: { bottom: 8, type: "scroll", padding: [4, 8] },
    },
    "financial-standard": {
        color: ["#1c7ed6", "#7950f2", "#12b886", "#f59f00", "#e03131"],
        grid: { left: 56, right: 32, bottom: 56, top: 40, containLabel: true },
        textStyle: { fontFamily: "'Noto Sans KR', sans-serif", fontSize: 11 },
        tooltip: { trigger: "axis", confine: true },
        legend: { bottom: 8, type: "scroll", padding: [4, 8] },
    },
    default: {
        color: ["#2563EB", "#7C3AED", "#059669", "#D97706"],
        grid: { left: 56, right: 32, bottom: 48, top: 36, containLabel: true },
        legend: { bottom: 8, type: "scroll", padding: [4, 8] },
        tooltip: { confine: true },
    },
};

function deepMerge<T extends Record<string, unknown>>(base: T, patch: Record<string, unknown>): T {
    const out: Record<string, unknown> = { ...base };
    for (const [key, val] of Object.entries(patch)) {
        const prev = out[key];
        if (isPlainObject(prev) && isPlainObject(val)) {
            out[key] = deepMerge(prev, val);
        } else if (val !== undefined) {
            out[key] = val;
        }
    }
    return out as T;
}

function normalizeGridValue(grid: EChartsOption["grid"]): Record<string, unknown> {
    if (!grid) return {};
    if (Array.isArray(grid)) return { ...(grid[0] as Record<string, unknown> ?? {}) };
    return { ...(grid as Record<string, unknown>) };
}

function normalizeLegendList(legend: EChartsOption["legend"]): Record<string, unknown>[] {
    if (!legend) return [];
    if (Array.isArray(legend)) {
        return legend.filter(isPlainObject) as Record<string, unknown>[];
    }
    return isPlainObject(legend) ? [legend] : [];
}

function legendHasData(legend: Record<string, unknown>): boolean {
    const data = legend.data;
    if (Array.isArray(data)) return data.length > 0;
    return legend.show !== false;
}

function hasVisibleLegend(option: EChartsOption): boolean {
    return normalizeLegendList(option.legend).some(legendHasData);
}

function isBottomLegend(legend: Record<string, unknown>): boolean {
    if (legend.show === false) return false;
    const top = legend.top;
    if (top !== undefined && top !== null && top !== "auto") return false;
    return true;
}

function hasBottomLegend(option: EChartsOption): boolean {
    const legends = normalizeLegendList(option.legend);
    if (legends.length === 0) return false;
    return legends.some(entry => legendHasData(entry) && isBottomLegend(entry));
}

function normalizeAxisList(axis: unknown): Record<string, unknown>[] {
    if (!axis) return [];
    if (Array.isArray(axis)) {
        return axis.filter(isPlainObject) as Record<string, unknown>[];
    }
    return isPlainObject(axis) ? [axis] : [];
}

function hasRotatedXAxisLabels(option: EChartsOption): boolean {
    return normalizeAxisList(option.xAxis).some(axis => {
        const rotate = (axis.axisLabel as { rotate?: number } | undefined)?.rotate;
        return typeof rotate === "number" && Math.abs(rotate) > 0;
    });
}

function countYAxes(option: EChartsOption): number {
    return normalizeAxisList(option.yAxis).length;
}

function hasInternalTitle(option: EChartsOption): boolean {
    const title = option.title;
    if (!title) return false;
    if (Array.isArray(title)) {
        return title.some(entry => isPlainObject(entry) && Boolean(String(entry.text ?? "").trim()));
    }
    if (isPlainObject(title)) {
        return Boolean(String(title.text ?? "").trim());
    }
    return false;
}

function hasDataZoom(option: EChartsOption): boolean {
    return Boolean(option.dataZoom && (Array.isArray(option.dataZoom) ? option.dataZoom.length > 0 : true));
}

function toNumber(value: unknown, fallback: number): number {
    return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

/** 범례·축 라벨·이중 Y축 등에 맞춰 grid/legend 여백 보정 */
function polishReportChartLayout(option: EChartsOption): EChartsOption {
    const grid = normalizeGridValue(option.grid);
    let bottom = toNumber(grid.bottom, 48);
    let top = toNumber(grid.top, 36);
    let left = toNumber(grid.left, 56);
    let right = toNumber(grid.right, 32);

    if (hasBottomLegend(option)) {
        bottom = Math.max(bottom, 72);
    }
    if (hasRotatedXAxisLabels(option)) {
        bottom = Math.max(bottom, 96);
    }
    if (hasDataZoom(option)) {
        bottom = Math.max(bottom, 80);
    }
    if (countYAxes(option) >= 2) {
        left = Math.max(left, 64);
        right = Math.max(right, 48);
    } else if (countYAxes(option) === 1) {
        left = Math.max(left, 56);
    }
    if (hasInternalTitle(option)) {
        top = Math.max(top, 52);
    }
    if (hasVisibleLegend(option) && !hasBottomLegend(option)) {
        top = Math.max(top, 48);
    }

    const polishedLegend = normalizeLegendList(option.legend).map(entry => {
        if (!legendHasData(entry) || !isBottomLegend(entry)) return entry;
        const currentBottom = toNumber(entry.bottom, 0);
        return {
            ...entry,
            bottom: currentBottom > 0 ? currentBottom : 8,
            type: entry.type ?? "scroll",
            padding: entry.padding ?? [4, 8],
        };
    });

    return {
        ...option,
        grid: {
            ...grid,
            left,
            right,
            top,
            bottom,
            containLabel: grid.containLabel ?? true,
        },
        ...(polishedLegend.length > 0
            ? { legend: Array.isArray(option.legend) ? polishedLegend : polishedLegend[0] }
            : {}),
    };
}

/** 차트 복잡도에 따른 렌더 높이 (px) */
export function resolveReportChartHeight(option: EChartsOption, baseHeight: number): number {
    let height = baseHeight;
    if (hasBottomLegend(option)) height += 28;
    if (hasRotatedXAxisLabels(option)) height += 36;
    if (hasDataZoom(option)) height += 16;
    if (hasInternalTitle(option)) height += 12;
    if (countYAxes(option) >= 2) height += 12;
    return Math.min(Math.max(height, baseHeight), 560);
}

/** template_id / pattern_id 기반 ECharts 테마 병합 */
export function applyReportChartTheme(
    option: EChartsOption,
    templateId?: string,
    patternId?: string,
): EChartsOption {
    const key = templateId || patternId || "default";
    const preset = CHART_THEME_PRESETS[key] ?? CHART_THEME_PRESETS.default;
    let merged: EChartsOption;
    if (key !== "default" && key !== "analytical-standard" && key !== "financial-standard" && patternId) {
        const patternPreset = CHART_THEME_PRESETS[patternId];
        if (patternPreset) {
            merged = deepMerge(
                deepMerge(preset as Record<string, unknown>, patternPreset as Record<string, unknown>),
                option as Record<string, unknown>,
            ) as EChartsOption;
        } else {
            merged = deepMerge(preset as Record<string, unknown>, option as Record<string, unknown>) as EChartsOption;
        }
    } else {
        merged = deepMerge(preset as Record<string, unknown>, option as Record<string, unknown>) as EChartsOption;
    }
    return polishReportChartLayout(merged);
}

export type EchartPresentation = {
    option: EChartsOption | null;
    title?: string;
    subtitle?: string;
    insight?: string;
};

/** API/LLM 응답의 echart payload → option + 메타 정규화 */
export function normalizeEchartPresentation(data: ReportBlockData): EchartPresentation {
    if (!isPlainObject(data)) {
        return { option: null };
    }

    const raw = data as Record<string, unknown>;
    let title: string | undefined;
    let subtitle: string | undefined;
    let insight: string | undefined;

    const rawTitle = raw.title;
    if (typeof rawTitle === "string") title = rawTitle;
    else if (isPlainObject(rawTitle) && typeof rawTitle.text === "string") title = rawTitle.text;

    if (typeof raw.subtitle === "string") subtitle = raw.subtitle;
    if (typeof raw.insight === "string") insight = raw.insight;

    const option = normalizeEchartOption(data);
    return { option, title, subtitle, insight };
}

/** API/LLM 응답의 echart payload → echarts-for-react option 정규화 */
export function normalizeEchartOption(data: ReportBlockData): EChartsOption | null {
    if (!isPlainObject(data)) return null;

    const raw = data as Record<string, unknown>;

    if (raw.type === "echarts" && isPlainObject(raw.value) && looksLikeEchartOption(raw.value)) {
        return stripEchartMetaFields(raw.value);
    }

    const wrappedKeys = ["option", "chart_option", "echarts_option", "echart_option"] as const;
    for (const key of wrappedKeys) {
        const nested = raw[key];
        if (isPlainObject(nested) && looksLikeEchartOption(nested)) {
            return stripEchartMetaFields(nested);
        }
        if (typeof nested === "string") {
            try {
                const parsed = JSON.parse(nested) as unknown;
                if (isPlainObject(parsed) && looksLikeEchartOption(parsed)) {
                    return stripEchartMetaFields(parsed);
                }
            } catch {
                // ignore
            }
        }
    }

    if (looksLikeEchartOption(raw)) {
        return stripEchartMetaFields(raw);
    }

    return null;
}

export function isEchartBlockData(data: ReportBlockData): boolean {
    return normalizeEchartOption(data) != null;
}
