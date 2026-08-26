import type { QueryType } from "./queryTypeHeuristic";

export type CountEntry = {
    label: string;
    value: number;
};

export type SourceTypeCounts = {
    file: number;
    tool: number;
    db: number;
    other: number;
};

export type SchemaMappingStats = {
    mapped: number;
    unmapped: number;
    total: number;
    ratio: number;
};

export type RecommendedQueryItem = {
    query: string;
    modelDid: string;
    modelName: string;
};

export type QueryLengthStats = {
    average: number;
    min: number;
    max: number;
    withQuery: number;
    buckets: CountEntry[];
};

export type QueryTypeStats = {
    types: Record<QueryType, number>;
    total: number;
};

export type DashboardAggregates = {
    kpi: {
        /** completed 분석 모델 (= pangeaze All-in-One으로 생산, 통합 스키마 포함) */
        modelCount: number;
        reportCount: number;
        toolCount: number;
    };
    modelCategories: CountEntry[];
    sourceTypeCounts: SourceTypeCounts;
    schemaMapping: SchemaMappingStats;
    recentModels: Array<{
        did: string;
        name: string;
        category: string;
        sourceSummary: string;
        hasSchema: boolean;
        suggestedQueryCount: number;
    }>;
    recommendedQueries: RecommendedQueryItem[];
    reportModelUsage: CountEntry[];
    reportQueryTypes: QueryTypeStats;
    reportQueryLength: QueryLengthStats;
    reportToolUsage: CountEntry[];
    reportSchemaLinkedCount: number;
    recentReports: Array<{
        rid: string;
        title: string;
        modelName: string;
        queryPreview: string;
        toolCount: number;
    }>;
    toolCategories: CountEntry[];
    toolProviders: CountEntry[];
    toolStatusCounts: CountEntry[];
    toolTags: CountEntry[];
};
