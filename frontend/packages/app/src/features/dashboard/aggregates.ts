import type { SageData, DataSource } from "@/features/data";
import type { ReportListItem } from "@/features/report-management/reportListTypes";
import type { Tool } from "@/features/tool";
import { resolveHasActiveSchema } from "@/libs/stores/dataManagement/schemaResolver";
import { getCategoryLabel, getProviderLabel, resolveCategoryCode } from "@/libs/stores/toolManagement/commonCodes";
import {
    QUERY_TYPE_LABELS,
    resolveQueryType,
    type QueryType,
} from "./queryTypeHeuristic";
import type {
    CountEntry,
    DashboardAggregates,
    RecommendedQueryItem,
    SourceTypeCounts,
} from "./types";

const SOURCE_TYPE_LABELS: Record<string, string> = {
    file: "파일",
    tool: "도구",
    db: "DB",
};

function countByField(items: string[]): CountEntry[] {
    const map = new Map<string, number>();
    for (const item of items) {
        map.set(item, (map.get(item) ?? 0) + 1);
    }
    return [...map.entries()]
        .map(([label, value]) => ({ label, value }))
        .sort((a, b) => b.value - a.value);
}

function topN(entries: CountEntry[], n: number): CountEntry[] {
    return entries.slice(0, n);
}

function normalizeSourceType(type: string): keyof SourceTypeCounts {
    const lower = type.toLowerCase();
    if (lower === "file" || lower === "tool" || lower === "db") return lower;
    return "other";
}

function summarizeSources(sources?: DataSource[]): string {
    if (!sources?.length) return "-";
    const counts: Record<string, number> = {};
    for (const src of sources) {
        const key = SOURCE_TYPE_LABELS[normalizeSourceType(src.type)] ?? src.type;
        counts[key] = (counts[key] ?? 0) + 1;
    }
    return Object.entries(counts)
        .map(([label, count]) => `${label} ${count}`)
        .join(" · ");
}

function aggregateSourceTypes(models: SageData[]): SourceTypeCounts {
    const result: SourceTypeCounts = { file: 0, tool: 0, db: 0, other: 0 };
    for (const model of models) {
        for (const src of model.sources ?? []) {
            result[normalizeSourceType(src.type)] += 1;
        }
    }
    return result;
}

function collectRecommendedQueries(models: SageData[], limit: number): RecommendedQueryItem[] {
    const items: RecommendedQueryItem[] = [];
    const reversed = [...models].reverse();
    for (const model of reversed) {
        const queries = model.suggested_queries ?? [];
        for (const query of queries) {
            const trimmed = query.trim();
            if (!trimmed) continue;
            items.push({
                query: trimmed,
                modelDid: model.did,
                modelName: model.name,
            });
            if (items.length >= limit) return items;
        }
    }
    return items;
}

function buildModelNameMap(models: SageData[]): Map<string, string> {
    return new Map(models.map(m => [m.did, m.name]));
}

function buildQueryLengthStats(reports: ReportListItem[]): DashboardAggregates["reportQueryLength"] {
    const lengths = reports
        .map(r => r.query?.trim().length ?? 0)
        .filter(len => len > 0);

    const buckets: CountEntry[] = [
        { label: "~49자", value: 0 },
        { label: "50~99자", value: 0 },
        { label: "100~149자", value: 0 },
        { label: "150~199자", value: 0 },
        { label: "200자+", value: 0 },
    ];

    for (const len of lengths) {
        if (len < 50) buckets[0].value += 1;
        else if (len < 100) buckets[1].value += 1;
        else if (len < 150) buckets[2].value += 1;
        else if (len < 200) buckets[3].value += 1;
        else buckets[4].value += 1;
    }

    if (lengths.length === 0) {
        return {
            average: 0,
            min: 0,
            max: 0,
            withQuery: 0,
            buckets,
        };
    }

    const sum = lengths.reduce((acc, n) => acc + n, 0);
    return {
        average: Math.round(sum / lengths.length),
        min: Math.min(...lengths),
        max: Math.max(...lengths),
        withQuery: lengths.length,
        buckets,
    };
}

function buildQueryTypeStats(reports: ReportListItem[]): DashboardAggregates["reportQueryTypes"] {
    const types: Record<QueryType, number> = {
        short: 0,
        exploratory: 0,
        detailed: 0,
    };
    let total = 0;
    for (const report of reports) {
        const type = resolveQueryType(report);
        if (!type) continue;
        types[type] += 1;
        total += 1;
    }
    return { types, total };
}

const TOOL_STATUS_LABELS: Record<string, string> = {
    assetized: "자산등록",
    generated: "생성등록",
    "syntax-passed": "구문통과",
    validated: "검증완료",
    failed: "실패",
};

export function buildDashboardAggregates(
    models: SageData[],
    reports: ReportListItem[],
    tools: Tool[],
): DashboardAggregates {
    const modelNameMap = buildModelNameMap(models);
    const schemaTotal = models.length;
    const mappedCount = models.filter(m => resolveHasActiveSchema(m)).length;

    const modelCategories = countByField(
        models.map(m => {
            const code = resolveCategoryCode(m.category);
            return getCategoryLabel(code);
        }),
    );

    const sourceTypeCounts = aggregateSourceTypes(models);

    const recentModels = [...models].reverse().slice(0, 5).map(m => ({
        did: m.did,
        name: m.name,
        category: getCategoryLabel(resolveCategoryCode(m.category)),
        sourceSummary: summarizeSources(m.sources),
        hasSchema: resolveHasActiveSchema(m),
        suggestedQueryCount: m.suggested_queries?.length ?? 0,
    }));

    const reportModelUsage = topN(
        countByField(
            reports
                .map(r => (r.did ? modelNameMap.get(r.did) ?? r.did : "미지정"))
                .filter(Boolean),
        ),
        5,
    );

    const reportToolUsage = topN(
        countByField(reports.flatMap(r => r.tools ?? [])),
        5,
    );

    const reportSchemaLinkedCount = reports.filter(r => {
        if (!r.did) return false;
        const model = models.find(m => m.did === r.did);
        return model ? resolveHasActiveSchema(model) : false;
    }).length;

    const recentReports = [...reports].reverse().slice(0, 5).map(r => ({
        rid: r.rid,
        title: r.title?.trim() || r.description?.trim() || r.rid,
        modelName: r.did ? modelNameMap.get(r.did) ?? r.did : "미지정",
        queryPreview: r.query?.trim()
            ? r.query.trim().length > 60
                ? `${r.query.trim().slice(0, 60)}…`
                : r.query.trim()
            : "-",
        toolCount: r.tools?.length ?? 0,
    }));

    const toolCategories = countByField(
        tools.map(t => {
            const code = resolveCategoryCode(t.category);
            return getCategoryLabel(code);
        }),
    );

    const toolProviders = countByField(
        tools.map(t => {
            const raw = t.secret_id ?? t.caller ?? t.provider ?? "미지정";
            return getProviderLabel(raw) !== raw ? getProviderLabel(raw) : raw;
        }),
    );

    const toolStatusCounts = countByField(
        tools.map(t => TOOL_STATUS_LABELS[t.status] ?? t.status),
    );

    const toolTags = topN(
        countByField(tools.flatMap(t => t.tags ?? [])),
        10,
    );

    const queryTypeStats = buildQueryTypeStats(reports);

    return {
        kpi: {
            modelCount: models.length,
            reportCount: reports.length,
            toolCount: tools.length,
        },
        modelCategories,
        sourceTypeCounts,
        schemaMapping: {
            mapped: mappedCount,
            unmapped: schemaTotal - mappedCount,
            total: schemaTotal,
            ratio: schemaTotal > 0 ? Math.round((mappedCount / schemaTotal) * 100) : 0,
        },
        recentModels,
        recommendedQueries: collectRecommendedQueries(models, 8),
        reportModelUsage,
        reportQueryTypes: queryTypeStats,
        reportQueryLength: buildQueryLengthStats(reports),
        reportToolUsage,
        reportSchemaLinkedCount,
        recentReports,
        toolCategories,
        toolProviders,
        toolStatusCounts,
        toolTags,
    };
}

export function formatSourceTypeCounts(counts: SourceTypeCounts): CountEntry[] {
    return [
        { label: "파일", value: counts.file },
        { label: "도구", value: counts.tool },
        { label: "DB", value: counts.db },
        ...(counts.other > 0 ? [{ label: "기타", value: counts.other }] : []),
    ];
}

export function formatQueryTypeCounts(stats: DashboardAggregates["reportQueryTypes"]): CountEntry[] {
    return (Object.keys(QUERY_TYPE_LABELS) as QueryType[])
        .map(type => ({
            label: QUERY_TYPE_LABELS[type],
            value: stats.types[type],
        }))
        .filter(entry => entry.value > 0);
}
