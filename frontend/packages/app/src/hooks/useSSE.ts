import {useEffect, useCallback, useRef} from 'react';
import {type QueryKey, useMutation, useQueryClient} from "@tanstack/react-query";
import {appendApiKeyQuery, getSageApiKeyHeaders} from "@/features/Utils.ts";

export type SseEvent<T = unknown> = {
    event: string;
    data: T;
    id?: string;
}

export type UsePostSseOptions<TEventData, TCache> = {
    url: string;
    queryKey: QueryKey;
    reducer: (oldData: TCache | undefined, event: SseEvent<TEventData>) => TCache;
    headers?: Record<string, string>;
    credentials?: RequestCredentials;
    fetchOptions?: Omit<RequestInit, "method" | "body" | "headers" | "signal">;
    initialData?: TCache;
    onEvent?: (event: SseEvent<TEventData>) => void;
    onComplete?: () => void;
}

export function useSseMutation<TPayload, TEventData, TCache>({
    url,
    queryKey,
    reducer,
    headers,
    fetchOptions,
    initialData,
    onEvent,
    onComplete,
}: UsePostSseOptions<TEventData, TCache>) {
    const queryClient = useQueryClient();
    const abortRef = useRef<AbortController | null>(null);

    const close = useCallback(() => {
        abortRef.current?.abort();
        abortRef.current = null;
    }, []);

    useEffect(() => {
        return () => {
           close();
        }
    }, [close]);

    const mutation = useMutation({
        mutationFn: async (payload: TPayload) => {
            // 기존 연결 해제
            close();

            const controller = new AbortController();
            abortRef.current = controller;

            if (initialData !== undefined) {
                queryClient.setQueryData<TCache>(queryKey, initialData);
            }

            const securedUrl = appendApiKeyQuery(url);

            const response = await fetch(securedUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                    ...getSageApiKeyHeaders(url),
                    ...headers
                },
                body: JSON.stringify(payload),
                signal: controller.signal,
                credentials: "include",
                ...fetchOptions
            });

            if (!response.ok) {
                throw new Error(`SSE request failed. ${response.status} ${response.statusText}`);
            }

            if (!response.body) {
                throw new Error("ReadableStream is not available on this response");
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            try {
                while(true) {
                    const {value, done} = await reader.read();

                    if (done) {
                        break;
                    }

                    buffer += decoder.decode(value, {stream: true});

                    const {events, rest} = parseSseChunk(buffer);
                    buffer = rest;

                    for(const item of events) {
                        // 파싱되지 않은 event는 무시
                        if (!item.parsed) {
                            continue;
                        }

                        const parsedEvent: SseEvent<TEventData> = {
                            event: item.parsed.event,
                            id: item.parsed.id,
                            data: JSON.parse(item.parsed.data),
                        }

                        onEvent?.(parsedEvent);

                        queryClient.setQueryData<TCache>(queryKey, old =>
                            reducer(old, parsedEvent),
                        );
                    }
                }

                onComplete?.();
                return {completed: true as const}
            } finally {
                reader.releaseLock();
                abortRef.current = null;
            }
        }
    })

    return {
        ...mutation,
        startStream: mutation.mutate,
        startStreamAsync: mutation.mutateAsync,
        close,
        isStreaming: mutation.isPending
    }
}

/**
 *
 * @param buffer
 */
function parseSseChunk(buffer: string): {
    events: Array<{ raw: string, parsed: SseEvent<string> | null }>;
    rest: string;
} {
    const parts = buffer.split("\n\n");
    const complete = parts.slice(0, -1);
    const rest = parts[parts.length - 1] ?? "";

    const events = complete.map((raw) => {
        const lines = raw.split("\n");
        let event = "message";
        let id: string | undefined;
        const dataLines: string[] = [];

        // event, data 추출
        for (const line of lines) {
            // ping
            if (line.startsWith(":")) {
                continue;
            }

            // event
            if (line.startsWith("event:")) {
                event = line.slice(6).trim();
                continue;
            }

            // id
            if (line.startsWith("id:")) {
                event = line.slice(3).trim();
                continue;
            }

            // data
            if (line.startsWith("data:")) {
                dataLines.push(line.slice(5).trimStart());
            }
        }

        const data = dataLines.join("\n");

        if (!data && !event && !id) {
            return { raw, parsed: null };
        }

        return {
            raw,
            parsed: {
                event: event,
                id: id,
                data: data
            }
        };
    });

    return {
        events: events,
        rest: rest,
    }
}