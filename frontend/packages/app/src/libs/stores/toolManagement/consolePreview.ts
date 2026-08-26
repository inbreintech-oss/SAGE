/** 트랜잭션 콘솔 — raw json response 패널용 스냅샷 (store 레이어) */

export function formatTraceTimestamp(date = new Date()): string {
    return date.toISOString().replace("T", " ").slice(0, 19);
}

export function buildConsoleWaitingPreview(phase: "idle" | "new" | "selected"): string {
    const hints: Record<typeof phase, string> = {
        idle: "도구를 선택하거나 [신규 도구]로 등록을 시작하면 SSE·API 트랜잭션이 이곳에 표시됩니다.",
        new: "POST /tool/generate SSE 스트림의 completed 이벤트 payload가 이곳에 표시됩니다.",
        selected: "POST /tool/exec 응답 result 객체가 이곳에 표시됩니다. [미리보기 실행]을 눌러 주세요.",
    };

    return JSON.stringify(
        {
            status: "waiting",
            phase,
            message: hints[phase],
            panels: {
                trace: "standard system trace — 단계별 [SYSTEM]/[TRACE]/[SUCCESS]/[ERROR] 로그",
                json: "raw json response — API 요청·응답 JSON 스냅샷",
            },
        },
        null,
        2,
    );
}

export function buildToolSyncResultPreview(input: {
    phase: "generate" | "update";
    endpoint: string;
    toolId: string;
    title: string;
    description?: string;
    codeLength: number;
    execQuery?: string;
    preserveQuery: string;
    queryExamples?: string[] | null;
    caller?: string;
}): string {
    return JSON.stringify(
        {
            phase: input.phase,
            endpoint: input.endpoint,
            status: "completed",
            tool_id: input.toolId,
            applied_from_server: {
                description: input.description?.trim() || null,
                code_bytes: input.codeLength,
                exec_query: input.execQuery?.trim() || null,
            },
            preserved_user_input: {
                title: input.title,
                save_query: input.preserveQuery,
            },
            query_examples: input.queryExamples ?? null,
            caller: input.caller ?? null,
        },
        null,
        2,
    );
}

/** @deprecated buildToolSyncResultPreview 사용 */
export function buildGenerateResultPreview(input: {
    toolId: string;
    title: string;
    description?: string;
    codeLength: number;
    execQuery?: string;
    preserveQuery: string;
    queryExamples?: string[] | null;
    caller?: string;
}): string {
    return buildToolSyncResultPreview({
        phase: "generate",
        endpoint: "POST /tool/generate",
        ...input,
    });
}

export function buildExecRequestPreview(input: {
    toolId: string;
    tokenToolId?: string | null;
    query: string;
    tools: string[];
}): string {
    return JSON.stringify(
        {
            phase: "exec",
            endpoint: "POST /tool/exec",
            status: "request",
            payload: {
                tools: input.tools,
                query: input.query,
            },
            meta: {
                main_tool_id: input.toolId,
                token_tool_id: input.tokenToolId?.trim() || null,
            },
        },
        null,
        2,
    );
}

export function buildExecResponsePreview(input: {
    toolId: string;
    success: boolean;
    result: unknown;
    error?: string | null;
}): string {
    return JSON.stringify(
        {
            phase: "exec",
            endpoint: "POST /tool/exec",
            status: input.success ? "completed" : "error",
            tool_id: input.toolId,
            success: input.success,
            error: input.error ?? null,
            result: input.result,
        },
        null,
        2,
    );
}
