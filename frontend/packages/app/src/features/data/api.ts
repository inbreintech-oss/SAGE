import { FetchAPI, FetchAPIError } from "@/features/Utils.ts";
import { sortSageDataList } from "@/libs/sortListItems";
import type { DataSourceColumn, DataSourceOptions, DataSourceSheet } from "./sourceSchema";

export type { DataSourceColumn, DataSourceOptions, DataSourceSheet } from "./sourceSchema";

/* ── 원천 소스 단일 항목 타입 (Data API v1.1) ─────────────────── */
export type DataSource = {
    /** "file" | "tool" | "db" 등 */
    type: string;
    /** 원본 경로 (ex: "uploaded/stocks.csv") */
    path: string;
    format?: string;
    options?: DataSourceOptions;
    /** v1.1 — 선택 시트·컬럼 (file / db) */
    sheets?: DataSourceSheet[];
    /** @deprecated v1.1 — sheets 사용 */
    columns?: string[];
    id?: string;
    origin?: string;
};

export type SageData = {
    did: string;
    name: string;
    status: string;
    description: string;
    /** 원천 소스 목록 (file / tool / db) */
    sources?: DataSource[];
    /** 추후 list/detail API — 통합 스키마 존재 여부 */
    has_schema?: boolean;
    /** 모델별 추천 질의문 (List Data / Pangeaze) */
    suggested_queries?: string[];
    /** Pangea 스키마 버전 목록 (List Data) */
    pangea?: unknown[];
    /** 분석 카테고리 (Data API v1.3) */
    category?: string;
    created_at?: string;
    updated_at?: string;
};

/** POST /data/list/query — item.status (OR 조건) */
export type DataApiStatus = "ready" | "completed" | "failed" | string;

export type DataListQueryPayload = {
    /** 미전달·빈 배열이면 전체 조회 */
    status?: DataApiStatus[];
};

export type DataListQueryParams = {
    status?: DataApiStatus[];
};

export type DataListResultItem = {
    did?: string;
    _id?: string;
    name: string;
    status: string;
    description: string;
    sources?: DataSource[];
    has_schema?: boolean;
    suggested_queries?: string[];
    pangea?: unknown[];
    category?: string;
    created_at?: string;
    updated_at?: string;
};

export type DataListResponse = {
    success: boolean;
    error: string | null;
    result: DataListResultItem[];
};

function resolveDid(item: DataListResultItem): string {
    return item.did ?? item._id ?? "";
}

function mapDataListItem(item: DataListResultItem): SageData {
    return {
        did: resolveDid(item),
        name: item.name,
        status: item.status,
        description: item.description,
        sources: item.sources ?? [],
        ...(item.has_schema !== undefined ? { has_schema: item.has_schema } : {}),
        ...(item.suggested_queries !== undefined
            ? { suggested_queries: item.suggested_queries }
            : {}),
        ...(item.pangea !== undefined ? { pangea: item.pangea } : {}),
        ...(item.category !== undefined ? { category: item.category } : {}),
        ...(item.created_at !== undefined ? { created_at: item.created_at } : {}),
        ...(item.updated_at !== undefined ? { updated_at: item.updated_at } : {}),
    };
}

/** POST /data/list/query — 데이터셋 목록 조회 */
export async function dataList(params?: DataListQueryParams): Promise<SageData[]> {
    const payload: DataListQueryPayload = {};
    if (params?.status?.length) {
        payload.status = [...params.status];
    }

    const response = await FetchAPI<DataListResponse>(
        "/api/data/list/query",
        "POST",
        { body: JSON.stringify(payload) },
    );

    if (!response.success) {
        throw new FetchAPIError({
            success: false,
            error: response.error ?? "데이터셋 목록 조회에 실패했습니다.",
        });
    }

    return sortSageDataList(
        (response.result ?? [])
            .map(mapDataListItem)
            .filter(item => item.did.length > 0),
    );
}

/** DELETE /data/delete — mode */
export type DataDeleteMode = "all" | "exclude" | "list";

export type DataDeletePayload = {
    /** mode=list|exclude 시 대상 did, mode=all 시 생략 가능 */
    ids?: string[];
    mode: DataDeleteMode;
};

type DataDeleteResponse =
    | string
    | { success?: boolean; error?: string | null; message?: string };

/** DELETE /data/delete — mode + JSON body (OpenAPI: delete_data_data_delete_delete) */
export async function deleteDataSets(payload: DataDeletePayload): Promise<string> {
    const response = await FetchAPI<DataDeleteResponse>(
        "/api/data/delete",
        "DELETE",
        { body: JSON.stringify(payload) },
    );

    if (typeof response === "object" && response !== null && response.success === false) {
        throw new FetchAPIError({
            success: false,
            error: response.error ?? "데이터셋 삭제에 실패했습니다.",
        });
    }

    if (typeof response === "string") return response;
    if (typeof response === "object" && response !== null && "message" in response) {
        return String((response as { message?: string }).message ?? "ok");
    }
    if (typeof response === "object" && response !== null && "status" in response) {
        return String((response as { status?: string }).status ?? "ok");
    }
    return "ok";
}

/** 단일 did 삭제 (mode: list) */
export async function deleteData(did: string): Promise<void> {
    await deleteDataSets({ ids: [did], mode: "list" });
}
