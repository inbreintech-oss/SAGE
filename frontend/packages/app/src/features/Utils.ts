import type {ApiResponseBase} from "@/libs/types";

/** FetchAPI / Tool API / SSE 등 다양한 에러 body 수용 */
export type FetchAPIErrorData = ApiResponseBase | Record<string, unknown>;

const SAGE_API_KEY_HEADER = "API-Key";

/** 백엔드 `.env` `SAGE_API_KEY` 와 동일 — Vite 클라이언트 번들용 */
export function getSageApiKey(): string {
    return (import.meta.env.VITE_SAGE_API_KEY ?? "").trim();
}

/** `/admin/*` 제외 SAGE REST·SSE 경로 — global API Key 대상 */
export function requiresSageApiKey(path: string): boolean {
    const pathname = path.split("?")[0];
    if (pathname.startsWith("/admin/")) {
        return false;
    }
    if (pathname.startsWith("/api/data") || pathname.startsWith("/api/report")) {
        return true;
    }
    if (pathname.startsWith("/tool/")) {
        return true;
    }
    if (pathname.startsWith("/secret")) {
        return true;
    }
    return false;
}

/** SSE 등 fetch 기반 스트림 — EventSource 호환을 위해 query param 추가 */
export function appendApiKeyQuery(url: string, apiKey?: string): string {
    const key = (apiKey ?? getSageApiKey()).trim();
    if (!key || !requiresSageApiKey(url)) {
        return url;
    }
    const separator = url.includes("?") ? "&" : "?";
    return `${url}${separator}api_key=${encodeURIComponent(key)}`;
}

/** REST/SSE fetch 헤더 — `API-Key` (백엔드 `sage/auth/api_key.py`) */
export function getSageApiKeyHeaders(path: string): Record<string, string> {
    const key = getSageApiKey();
    if (!key || !requiresSageApiKey(path)) {
        return {};
    }
    return {[SAGE_API_KEY_HEADER]: key};
}

/**
 * React Query 에러 핸들링을 위한 기본 Error 클래스입니다.
 */
export class FetchAPIError extends Error {
    data?: FetchAPIErrorData;

    constructor(data?: FetchAPIErrorData) {
        const message =
            (data as {message?: string} | undefined)?.message ??
            (data as {error?: string} | undefined)?.error ??
            "API request failed";
        super(message);
        this.data = data;
    }
}

/**
 *  * API 요청을 위한 Fetch Wrapper 입니다.
 * @param {string} path 요청 경로
 * @param {string} method 요청 메서드
 * @param {RequestInit} requestInit Request Options
 * @Template T 응답 데이터 타입
 * @returns {Promise<T>} 응답 데이터
 * @constructor
 */
export async function FetchAPI<T>(path: string, method: string, requestInit?: RequestInit): Promise<T> {

    // 1. FormData 여부 및 'file' 키 포함 여부 체크
    let isFileUpload = false;
    if (requestInit?.body instanceof FormData) {
        // FormData에 'file'이라는 키로 데이터가 들어있는지 확인
        if (requestInit.body.has("file")) {
            isFileUpload = true;
        }
    }
    // 2. 파일 업로드인 경우에만 헤더를 비우고, 그 외에는 기본 JSON 설정 적용
    const defaultHeaders: Record<string, string> = isFileUpload 
        ? {} 
        : { "Content-Type": "application/json" };


    const response: Response = await fetch(path, {
        method: method,
        headers: {
            ...defaultHeaders,
            ...getSageApiKeyHeaders(path),
            ...requestInit?.headers, // 사용자가 명시적으로 보낸 헤더가 있다면 우선함
        },
        credentials: "include",
        ...requestInit,
    });

    if (!response.ok) {
        let body = undefined;

        try {
            body = await response.json();
        } catch {
            // ignore
        }

        throw new FetchAPIError(body);
    }

    return response.json();
}

/**
 * GET 쿼리 생성 유틸입니다.
 * @param {string} path 요청 경로
 * @param {Record<string, string>} params 쿼리 파라미터
 * @returns {string} 생성된 GET 쿼리 문자열
 */
export function createGetQuery(path: string, params: Record<string, unknown>): string {
    const keys = Object.keys(params) as (keyof typeof params)[];
    const query = keys
        .filter(key => params[key] !== undefined && params[key] !== null)
        .map((key) => `${encodeURIComponent(key)}=${encodeURIComponent(String(params[key]))}`)
        .join("&");
    return path + (!path.endsWith("?") ? "?" : "") + query;
}

/**
 * Sleep 유틸입니다.
 * @param {number} ms 지연 시간 (밀리초)
 */
export async function sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * 더미 데이터를 반환하는 유틸 함수입니다.
 * @template T 반환할 데이터 타입
 * @param {number} ms 지연 시간 (밀리초)
 * @param {T} data 더미 데이터
 * @returns {Promise<T>}
 */
export async function getDummyData<T>(ms: number, data: T): Promise<T> {
    await sleep(ms);
    return data;
}

/**
 * fetch 요청 후 SSE 응답 스트림을 읽어 이벤트를 yield합니다.
 * @param url 요청 URL
 * @param init fetch 옵션
 */
export async function* fetchSSEStream(
    url: string,
    init: RequestInit,
    signal?: AbortSignal,
): AsyncGenerator<SSEEventData | string> {
    const securedUrl = appendApiKeyQuery(url);
    try {
        const response = await fetch(securedUrl, {
            ...init,
            signal,
            credentials: "include",
            headers: {
                "Content-Type": "application/json",
                "Accept": "text/stream-data",
                ...getSageApiKeyHeaders(url),
                ...init.headers,
            },
        });

        if (!response.ok) {
            yield `ERROR: ${response.status} ${response.statusText}`;
            return;
        }

        if (!response.body) {
            yield "ERROR: Response body is unavailable";
            return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";

        while (true) {
            const {value, done} = await reader.read();

            if (done) {
                if (buffer.trim()) {
                    const event = parseSSEEvent(buffer);
                    if (event) yield event;
                }
                break;
            }

            buffer += decoder.decode(value, {stream: true});
            buffer = buffer.replace(/\r\n/g, "\n");

            const parts = buffer.split("\n\n");
            buffer = parts.pop() ?? "";

            for (const part of parts) {
                if (!part.trim()) continue;
                const event = parseSSEEvent(part);
                if (event) yield event;
            }
        }
    } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
            return;
        }
        console.error(error);
        yield "ERROR: " + error;
    }
}

export type SSEEventData = {
    eventType: string;
    [key: string]: unknown;
}

/**
 * SSE 스트림을 소비하고 completed(또는 마지막) 이벤트를 반환합니다.
 * failed/error 이벤트 시 FetchAPIError를 throw합니다.
 */
export async function consumeSSEToCompletion(
    url: string,
    init: RequestInit,
    signal?: AbortSignal,
): Promise<SSEEventData> {
    const stream = fetchSSEStream(url, {
        credentials: "include",
        ...init,
        headers: {
            Accept: "text/event-stream",
            ...init.headers,
        },
    }, signal);

    let lastEvent: SSEEventData | null = null;

    for await (const chunk of stream) {
        if (typeof chunk === "string") {
            if (chunk.startsWith("ERROR:")) {
                throw new FetchAPIError({ success: false, error: chunk.slice(6).trim() });
            }
            continue;
        }

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

/**
 * SSE 이벤트 텍스트를 파싱합니다.
 * @param eventText 완성된 SSE 이벤트 문자열 (event: + data: 조합)
 */
function parseSSEDataPayload(dataRaw: string): {
    eventType?: string;
    eventData: Record<string, unknown>;
} | null {
    const trimmed = dataRaw.trim();
    if (!trimmed) return null;

    // 백엔드 중첩 형식: data: event: completed data: {"msg": "...", ...}
    const nested = trimmed.match(/^event:\s*(\S+)\s+data:\s*([\s\S]+)$/i);
    if (nested) {
        try {
            const eventData = JSON.parse(nested[2].trim()) as Record<string, unknown>;
            return { eventType: nested[1], eventData };
        } catch {
            console.debug("Failed to parse nested SSE JSON data %o", nested[2].slice(0, 200));
            return null;
        }
    }

    try {
        const eventData = JSON.parse(trimmed) as Record<string, unknown>;
        const embeddedEvent = typeof eventData.event === "string"
            ? eventData.event
            : typeof eventData.eventType === "string"
                ? eventData.eventType
                : undefined;
        return { eventType: embeddedEvent, eventData };
    } catch {
        console.debug("Failed to parse JSON data in SSE event %o", trimmed.slice(0, 200));
        return null;
    }
}

function parseSSEEvent(eventText: string): SSEEventData | null {
    let eventType = "unknown";
    const dataLines: string[] = [];

    for (const line of eventText.split("\n")) {
        if (line.startsWith(":")) continue;

        if (line.startsWith("event:")) {
            eventType = line.slice(6).trim();
            continue;
        }

        if (line.startsWith("data:")) {
            dataLines.push(line.slice(5).trimStart());
        }
    }

    const parsed = parseSSEDataPayload(dataLines.join("\n"));
    if (!parsed) return null;

    const resolvedType = parsed.eventType?.trim() || eventType;

    return {
        eventType: resolvedType,
        ...parsed.eventData,
    };
}

/** completed 이벤트 판별 — eventType 또는 tool_id+완료 메시지 */
export function isSSECompletedEvent(event: SSEEventData): boolean {
    const type = String(event.eventType ?? "").toLowerCase();
    if (type === "completed") return true;

    const toolId = resolveSSEEventToolId(event);

    const msg = String(event.msg ?? event.message ?? "");
    return Boolean(toolId) && msg.includes("완료");
}

function resolveSSEEventToolId(event: SSEEventData): string | undefined {
    if (typeof event.tool_id === "string" && event.tool_id.trim()) {
        return event.tool_id.trim();
    }

    const result = event.result;
    if (!result || typeof result !== "object") return undefined;

    if (Array.isArray(result)) {
        const first = result[0];
        if (first && typeof first === "object") {
            const id = (first as { tool_id?: string }).tool_id;
            return id?.trim() || undefined;
        }
        return undefined;
    }

    const obj = result as { tool_id?: string; result?: unknown };
    if (obj.tool_id?.trim()) return obj.tool_id.trim();

    if (Array.isArray(obj.result)) {
        const first = obj.result[0];
        if (first && typeof first === "object") {
            const id = (first as { tool_id?: string }).tool_id;
            return id?.trim() || undefined;
        }
    }

    return undefined;
}