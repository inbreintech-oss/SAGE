import {
    FetchAPI,
    FetchAPIError,
    fetchSSEStream,
    isSSECompletedEvent,
    type SSEEventData,
} from "@/features/Utils.ts";

import {
    collectQueryExamplesFromPayload,
    coerceQueryExamples,
    resolveGenerateResult,
    resolveToolIdFromGeneratePayload,
} from "@/features/tool-management/resolveQueryExamples";
import { filterTokenTools, TOKEN_TOOL_LIST_STATUSES } from "@/features/tool-management/filterTokenTools";



/** /tool/list/query — item.status */

export type ToolApiStatus =

    | "syntax-passed"

    | "validated"

    | "failed"

    | "assetized"

    | "generated";



/** toolList() params 미전달 시 fallback — 전역 도구 카탈로그 조회 */

export const DEFAULT_TOOL_LIST_STATUSES: readonly ToolApiStatus[] = [

    "assetized",

    "generated",

] as const;



export type Tool = {

    tool_id: string;

    title: string;

    description: string;

    code: string;

    caller: string | null;

    query_examples: string[] | null;

    category: string | null;

    tags: string[] | null;

    /** @deprecated API 응답은 secret_id 사용 */
    provider?: string | null;

    secret_id?: string | null;

    status: ToolApiStatus;

    created_at: string;

    updated_at: string;

};



export type ToolListQueryPayload = {

    category?: string;

    provider?: string[];

    /** 백엔드 ToolListRequest — 단일 secret_id 문자열 */
    secret_id?: string;

    status?: ToolApiStatus[];

    tags?: string[];

};



export type ToolListParams = {

    /** 미전달 시 assetized + generated (좌측 도구목록) */

    status?: ToolApiStatus[];

    category?: string;

    provider?: string[];

    secret_id?: string;

    tags?: string[];

};



export type ToolListResponse = {

    success: boolean;

    error: string | null;

    result: Tool[];

};



/** POST /tool/list/query — 조건 필터 목록 조회 */

export async function toolList(params?: ToolListParams): Promise<ToolListResponse> {

    const payload: ToolListQueryPayload = {

        status: params?.status ?? [...DEFAULT_TOOL_LIST_STATUSES],

    };

    if (params?.category) payload.category = params.category;

    if (params?.provider?.length) payload.provider = params.provider;

    const secretId = params?.secret_id?.trim();
    if (secretId) payload.secret_id = secretId;

    if (params?.tags?.length) payload.tags = [...params.tags];

    return FetchAPI("/tool/list/query", "POST", {

        body: JSON.stringify(payload),

    });

}



/**
 * POST /tool/list/query — 연계기관 인증 토큰 도구 목록
 *
 * 필터 (모두 AND, status·tags 내부는 OR):
 * - secret_id: 선택 Provider secret_id 와 동일
 * - status: assetized | generated (OR)
 * - tags: TOKEN_TOOL_TAGS 중 하나라도 도구 tags 에 포함 (OR)
 */
export async function toolListTokenTools(secretId: string): Promise<ToolListResponse> {
    const trimmed = secretId.trim();
    if (!trimmed) {
        return { success: true, error: null, result: [] };
    }

    const res = await toolList({
        secret_id: trimmed,
        status: [...TOKEN_TOOL_LIST_STATUSES],
    });

    if (!res.success) return res;

    const filtered = filterTokenTools(res.result ?? [], trimmed);
    return { ...res, result: filtered };
}

export { TOKEN_TOOL_LIST_STATUSES, TOKEN_TOOL_TAGS } from "@/features/tool-management/filterTokenTools";



export type SecretKeyItem = {

    secret_id: string;

    user_id: string;

    provider: string;

    keys: { key_name: string }[];

    description: string;

    created_at: string;

    updated_at: string;

};



export type SecretListResponse = {

    success: boolean;

    error: string | null;

    result: SecretKeyItem[];

};



/** POST /secret/list — 등록된 SecretKey 목록 (명세: No Parameters, 백엔드는 `{}` body 수용) */

export async function secretList(): Promise<SecretListResponse> {

    return FetchAPI("/secret/list", "POST", {

        body: JSON.stringify({}),

    });

}



export type ToolInfo = {

    tool_id: string;

    title: string;

    description: string;

    funcs: ToolFunc[];

    code: string;

    caller?: string;

    created_at?: string;

    updated_at?: string;

};



export type ToolFunc = {

    name: string;

    description: string;

    inputs: ToolParam[];

    outputs: ToolParam[];

};



export type ToolParam = {

    name: string;

    dtype: string;

    description: string | null;

    properties?: ToolParamProperty[];

};



export type ToolParamProperty = {

    name: string;

    dtype: string;

    description: string | null;

};



export type ToolInfoResponse = {

    success: boolean;

    error: string | null;

    result: ToolInfo;

};



export async function toolInfo(tool_id: string): Promise<ToolInfoResponse> {

    return FetchAPI(`/tool/info?tool_id=${encodeURIComponent(tool_id)}`, "GET");

}



export type ToolExecPayload = {

    tools: string[];

    query: string;

};



export type ToolExecResponse = {

    success: boolean;

    error: string | null;

    result: unknown;

};



export async function toolExec(payload: ToolExecPayload): Promise<ToolExecResponse> {

    return FetchAPI("/tool/exec", "POST", {

        body: JSON.stringify(payload),

    });

}



export type ToolGeneratePayload = {

    category: string;

    description: string;

    /** Tool API v1.3 — 도구 저장용 질의문 (생성 프롬프트) */
    query: string;

    /** Tool API v1.3 — 도구 저장용 예시 코드 (optional) */
    ref_code?: string;

    /** Tool API v1.3 — 연계기관 secret_id (optional) */
    secret_id?: string;

    tags: string[];

    tools: string[];

    user_id: string;

};



export type ToolGenerateResult = {

    tool_id: string;

    title?: string;

    description?: string;

    code?: string;

    caller?: string;

    query_examples?: string[] | null;

    category?: string;

    tags?: string[];

    secret_id?: string;

    status?: ToolApiStatus;

    created_at?: string;

    updated_at?: string;

};



export type ToolGenerateResponse = {

    msg?: string;

    tool_id?: string;

    /** v1.3 REST — result 배열; SSE는 mapToolSSEResponse에서 단일 객체로 정규화 */
    result?: ToolGenerateResult;

    success?: boolean;

    error?: string | null;

    detail?: string;

};



export type ToolSSEOptions = {

    onEvent?: (event: SSEEventData) => void;

    signal?: AbortSignal;

};



function mapToolSSEResponse(
    completed: SSEEventData,
    fallbackToolId?: string,
): {
    msg?: string;
    tool_id?: string;
    result?: ToolGenerateResult;
    success: true;
} {
    if (typeof completed.result === "string") {
        const message = completed.result.trim()
            || String(completed.msg ?? completed.message ?? "").trim()
            || undefined;
        return {
            msg: message,
            tool_id: (completed.tool_id as string | undefined) ?? fallbackToolId,
            success: true,
        };
    }

    const result = resolveGenerateResult(completed.result);

    const queryExamples = collectQueryExamplesFromPayload(completed)
        ?? collectQueryExamplesFromPayload(result);

    const mergedResult = result
        ? ({
            ...result,
            query_examples: queryExamples ?? coerceQueryExamples(result.query_examples),
        } as ToolGenerateResult)
        : undefined;

    return {
        msg: (completed.msg as string | undefined)
            ?? (typeof completed.message === "string" ? completed.message : undefined),
        tool_id: (completed.tool_id as string | undefined)
            ?? mergedResult?.tool_id
            ?? resolveToolIdFromGeneratePayload(completed.result)
            ?? fallbackToolId,
        result: mergedResult,
        success: true,
    };
}

function mapToolGenerateResponse(completed: SSEEventData): ToolGenerateResponse {
    return mapToolSSEResponse(completed);
}



async function runToolSSE(

    path: string,

    body: unknown,

    method: "POST" | "PATCH",

    options?: ToolSSEOptions,

): Promise<SSEEventData> {

    const stream = fetchSSEStream(

        path,

        {

            method,

            body: JSON.stringify(body),

            headers: {

                "Content-Type": "application/json",

                Accept: "text/event-stream",

            },

        },

        options?.signal,

    );



    let lastEvent: SSEEventData | null = null;



    for await (const chunk of stream) {

        if (typeof chunk === "string") {

            if (chunk.startsWith("ERROR:")) {

                throw new FetchAPIError({

                    success: false,

                    error: chunk.slice(6).trim(),

                });

            }

            continue;

        }



        options?.onEvent?.(chunk);

        lastEvent = chunk;



        if (chunk.eventType === "failed" || chunk.eventType === "error") {

            const message = String(

                chunk.msg ?? chunk.error ?? chunk.detail ?? "요청 처리에 실패했습니다.",

            );

            throw new FetchAPIError({

                success: false,

                error: message,

                detail: typeof chunk.detail === "string" ? chunk.detail : undefined,

            });

        }



        if (chunk.eventType === "completed" || isSSECompletedEvent(chunk)) {

            return chunk;

        }

    }



    if (lastEvent) {

        return lastEvent;

    }



    throw new FetchAPIError({

        success: false,

        error: "스트림이 종료되었으나 완료 이벤트를 수신하지 못했습니다.",

    });

}



export async function toolGenerate(

    payload: ToolGeneratePayload,

    options?: ToolSSEOptions,

): Promise<ToolGenerateResponse> {

    const completed = await runToolSSE("/tool/generate", payload, "POST", options);

    return mapToolGenerateResponse(completed);

}



export type ToolAssetizePayload = {

    asset_path: string;

    title: string;

    description: string;

    tool_id: string;

};



export type ToolAssetizeResponse = {

    success: boolean;

    error: string | null;

    result?: { asset_path: string; tool_id?: string };

    detail?: string;

};



export async function toolAssetize(payload: ToolAssetizePayload): Promise<ToolAssetizeResponse> {

    return FetchAPI("/tool/assetize", "POST", {

        body: JSON.stringify(payload),

    });

}



export type ToolDeleteMode = "all" | "exclude" | "list";

export type ToolDeletePayload = {
    /** mode=list|exclude 시 대상 tool_id, mode=all 시 생략 가능 */
    ids?: string[];
    mode: ToolDeleteMode;
};

export type ToolDeleteResponse = {

    success?: boolean;

    error?: string | null;

    detail?: string;

    msg?: string;

    status?: string;

    id?: string;

    message?: string;

};



/** DELETE /tool/delete — mode + JSON body */
export async function deleteTools(payload: ToolDeletePayload): Promise<ToolDeleteResponse> {

    return FetchAPI("/tool/delete", "DELETE", {

        body: JSON.stringify(payload),

    });

}



/** 단일 tool_id 삭제 (mode: list) */
export async function toolDelete(tool_id: string): Promise<ToolDeleteResponse> {

    return deleteTools({ mode: "list", ids: [tool_id] });

}



export type ToolUpdatePayload = {

    category: string;

    /** Tool API v1.3 — 수정 요약 코멘트 */
    comment: string;

    description: string;

    /** Tool API v1.3 — 도구 저장용 질의문 (수정 프롬프트) */
    query: string;

    /** Tool API v1.3 — 도구 저장용 예시 코드 (optional) */
    ref_code?: string;

    /** Tool API v1.3 — 연계기관 secret_id (optional) */
    secret_id?: string;

    tags: string[];

    tool_id: string;

    tools: string[];

};



export type ToolUpdateResponse = {

    success?: boolean;

    error?: string | null;

    detail?: string;

    msg?: string;

    tool_id?: string;

    result?: ToolGenerateResult;

};



export async function toolUpdate(

    payload: ToolUpdatePayload,

    options?: ToolSSEOptions,

): Promise<ToolUpdateResponse> {

    const completed = await runToolSSE("/tool/update", payload, "PATCH", options);

    return mapToolSSEResponse(completed, payload.tool_id);

}



export type ToolManagementExecPayload = {

    tool_id: string;

    parameters: Record<string, string>;

};



/** @deprecated 백엔드는 { query, tools } 만 수용 — toolExec 사용 */

export async function toolManagementExec(

    payload: ToolManagementExecPayload,

): Promise<ToolExecResponse> {

    return toolExec({

        tools: [payload.tool_id],

        query: JSON.stringify(payload.parameters),

    });

}



/** 1차 고정 — 서버 데이터 카테고리 협의 전까지 CAT_STOCK */
export const DEFAULT_TOOL_RECOMMEND_CATEGORY = "CAT_STOCK" as const;

export type ToolRecommendPayload = {
    did: string;
    /** 분석용 도구 카테고리 (1차: CAT_STOCK 고정) */
    tool_category?: string;
};

export type ToolRecommendResponse = {
    success: boolean;
    error: string | null;
    result: {
        recommended_tools: string[];
    };
};

/** POST /tool/recommend — 데이터셋 스키마 기반 분석 도구 추천 */
export async function recommendTools(
    payload: ToolRecommendPayload,
): Promise<string[]> {
    const body = {
        did: payload.did,
        tool_category: payload.tool_category ?? DEFAULT_TOOL_RECOMMEND_CATEGORY,
    };

    const response = await FetchAPI<ToolRecommendResponse>(
        "/tool/recommend",
        "POST",
        { body: JSON.stringify(body) },
    );

    if (!response.success) {
        throw new FetchAPIError({
            success: false,
            error: response.error ?? "도구 추천에 실패했습니다.",
        });
    }

    return response.result?.recommended_tools ?? [];
}

