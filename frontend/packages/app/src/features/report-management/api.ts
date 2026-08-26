import {
    consumeSSEToCompletion,
    FetchAPI,
    FetchAPIError,
    fetchSSEStream,
    type SSEEventData,
} from "@/features/Utils.ts";
import {
    isReportGenerateResult,
    unwrapReportGenerateResult,
    type ReportGenerateResult,
} from "./reportDocumentTypes";
import type {
    ExecReportPayload,
    PublishReportPayload,
    PublishReportResponse,
    ReportListItem,
    ReportListQueryPayload,
    ReportListQueryResponse,
} from "./reportListTypes";
import { sortReportListItems } from "@/libs/sortListItems";

export type GenerateReportSyncPayload = {
    did: string;
    query: string;
    tools: string[];
    /** Report API v1.1 — 화면 보고서명은 title 미지원 전 description 사용 */
    description: string;
};

export function extractReportFromSSEEvent(event: SSEEventData): ReportGenerateResult {
    const candidates: unknown[] = [
        event,
        event.result,
        event.data,
        event.report != null ? event : null,
    ];

    for (const candidate of candidates) {
        if (candidate == null) continue;

        if (typeof candidate === "string") {
            try {
                const parsed = JSON.parse(candidate) as unknown;
                if (isReportGenerateResult(parsed)) return parsed;
                return unwrapReportGenerateResult(parsed);
            } catch {
                continue;
            }
        }

        if (typeof candidate === "object") {
            try {
                if (isReportGenerateResult(candidate)) return candidate;
                return unwrapReportGenerateResult(candidate);
            } catch {
                // try next
            }
        }
    }

    if (event.report && typeof event.report === "object") {
        return {
            plan: event.plan as ReportGenerateResult["plan"],
            rid: typeof event.rid === "string" ? event.rid : undefined,
            report_dir: typeof event.report_dir === "string" ? event.report_dir : undefined,
            report: event.report as ReportGenerateResult["report"],
        };
    }

    throw new FetchAPIError({
        success: false,
        error: "보고서 결과(report)를 해석하지 못했습니다.",
    });
}

/** POST /report/generate — SSE */
export async function generateReportSync(
    payload: GenerateReportSyncPayload,
    signal?: AbortSignal,
): Promise<ReportGenerateResult> {
    const completed = await consumeSSEToCompletion(
        "/api/report/generate",
        {
            method: "POST",
            body: JSON.stringify(payload),
            headers: {
                "Content-Type": "application/json",
                Accept: "text/event-stream",
            },
        },
        signal,
    );

    return extractReportFromSSEEvent(completed);
}

/** POST /report/list/query */
export async function reportListQuery(
    payload: ReportListQueryPayload = {},
): Promise<ReportListItem[]> {
    const response = await FetchAPI<ReportListQueryResponse>(
        "/api/report/list/query",
        "POST",
        { body: JSON.stringify(payload) },
    );

    if (!response.success) {
        throw new FetchAPIError({
            success: false,
            error: response.error ?? "보고서 목록 조회에 실패했습니다.",
        });
    }

    return sortReportListItems(response.result ?? []);
}

/** POST /report/publish */
export async function publishReport(
    payload: PublishReportPayload,
): Promise<ReportListItem> {
    const response = await FetchAPI<PublishReportResponse>(
        "/api/report/publish",
        "POST",
        { body: JSON.stringify(payload) },
    );

    if (!response.success) {
        throw new FetchAPIError({
            success: false,
            error: response.error ?? "보고서 등록에 실패했습니다.",
        });
    }

    return response.result;
}

/** POST /report/exec — SSE, completed.result.report 사용 */
export async function execReportSync(
    payload: ExecReportPayload,
    signal?: AbortSignal,
): Promise<ReportGenerateResult> {
    const completed = await consumeSSEToCompletion(
        "/api/report/exec",
        {
            method: "POST",
            body: JSON.stringify(payload),
            headers: {
                "Content-Type": "application/json",
                Accept: "text/event-stream",
            },
        },
        signal,
    );

    return extractReportFromSSEEvent(completed);
}

/** generate/exec SSE 로그 스트리밍 (콘솔용) */
export async function* streamReportSSE(
    path: "/api/report/generate" | "/api/report/exec",
    body: unknown,
    signal?: AbortSignal,
): AsyncGenerator<SSEEventData | string> {
    const stream = fetchSSEStream(
        path,
        {
            method: "POST",
            body: JSON.stringify(body),
            headers: {
                "Content-Type": "application/json",
                Accept: "text/event-stream",
            },
        },
        signal,
    );

    for await (const chunk of stream) {
        yield chunk;
    }
}
