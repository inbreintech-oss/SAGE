import {
    extractReportFromSSEEvent,
    streamReportSSE,
    type GenerateReportSyncPayload,
} from "./api";
import type { ReportGenerateResult } from "./reportDocumentTypes";
import { FetchAPIError, type SSEEventData } from "@/features/Utils";

export type ReportStreamHandlers = {
    onLog?: (line: string) => void;
    onEvent?: (event: SSEEventData) => void;
};

function resolveHandlers(
    onLogOrHandlers: ((line: string) => void) | ReportStreamHandlers,
): ReportStreamHandlers {
    if (typeof onLogOrHandlers === "function") {
        return { onLog: onLogOrHandlers };
    }
    return onLogOrHandlers;
}

function emitChunk(
    chunk: SSEEventData | string,
    handlers: ReportStreamHandlers,
): void {
    if (typeof chunk === "string") {
        handlers.onLog?.(chunk);
        return;
    }
    handlers.onEvent?.(chunk);
    if (chunk.msg) handlers.onLog?.(String(chunk.msg));
}

/** generate SSE — 이벤트/로그 콜백 + 최종 report */
export async function generateReportWithLogs(
    payload: GenerateReportSyncPayload,
    onLogOrHandlers: ((line: string) => void) | ReportStreamHandlers,
    signal?: AbortSignal,
): Promise<ReportGenerateResult> {
    const handlers = resolveHandlers(onLogOrHandlers);
    let lastCompleted: ReportGenerateResult | null = null;

    for await (const chunk of streamReportSSE("/api/report/generate", payload, signal)) {
        if (typeof chunk === "string") {
            if (chunk.startsWith("ERROR:")) {
                throw new FetchAPIError({ success: false, error: chunk.slice(6).trim() });
            }
            emitChunk(chunk, handlers);
            continue;
        }

        emitChunk(chunk, handlers);

        if (chunk.eventType === "failed" || chunk.eventType === "error") {
            throw new FetchAPIError({
                success: false,
                error: String(chunk.msg ?? chunk.error ?? "보고서 생성에 실패했습니다."),
            });
        }

        if (chunk.eventType === "completed") {
            try {
                lastCompleted = extractReportFromSSEEvent(chunk);
            } catch {
                // completed but parse deferred
            }
        }
    }

    if (!lastCompleted) {
        throw new FetchAPIError({
            success: false,
            error: "보고서 생성이 완료되었으나 결과를 수신하지 못했습니다.",
        });
    }

    return lastCompleted;
}

/** exec SSE — 이벤트/로그 콜백 + 최종 report */
export async function execReportWithLogs(
    payload: { rid: string },
    onLogOrHandlers: ((line: string) => void) | ReportStreamHandlers,
    signal?: AbortSignal,
): Promise<ReportGenerateResult> {
    const handlers = resolveHandlers(onLogOrHandlers);
    let lastCompleted: ReportGenerateResult | null = null;

    for await (const chunk of streamReportSSE("/api/report/exec", payload, signal)) {
        if (typeof chunk === "string") {
            if (chunk.startsWith("ERROR:")) {
                throw new FetchAPIError({ success: false, error: chunk.slice(6).trim() });
            }
            emitChunk(chunk, handlers);
            continue;
        }

        emitChunk(chunk, handlers);

        if (chunk.eventType === "failed" || chunk.eventType === "error") {
            throw new FetchAPIError({
                success: false,
                error: String(chunk.msg ?? chunk.error ?? "보고서 실행에 실패했습니다."),
            });
        }

        if (chunk.eventType === "completed") {
            try {
                lastCompleted = extractReportFromSSEEvent(chunk);
            } catch {
                // defer
            }
        }
    }

    if (!lastCompleted) {
        throw new FetchAPIError({
            success: false,
            error: "보고서 실행이 완료되었으나 결과를 수신하지 못했습니다.",
        });
    }

    return lastCompleted;
}
