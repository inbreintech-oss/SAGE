import {mutationOptions, type QueryClient, queryOptions} from "@tanstack/react-query";
import {
    analyzeSchema, type AnalyzeSchemaPayload, type AnalyzeSchemaResponse, pangeaze, type PangeazePayload,
    type PangeazeResponse,
    registerData,
    type RegisterDataPayload,
    unifySchema, type UnifySchemaPayload, type UnifySchemaResponse, updatePangeaze, type UpdatePangeazePayload,
    type UpdatePangeazeResponse,
    type UploadDataPayload
} from "./api";

export const keys = {
    all: () => ["data-analysis"],
    upload: (payload: UploadDataPayload) => ["data-analysis", "upload", payload.file?.name],
    register: () => ["data-analysis", "register"],
    analyze: (did?: string) => ["data-analysis", "analyze", did],
    unify: (did?: string) => ["data-analysis", "unify", did],
    pangeaze: () => ["data-analysis", "pangeaze"],
    updatePangeaze: (did?: string) => ["data-analysis", "updatePangeaze", did],
} as const;

export const queries = {
    analyzeSchema: (did?: string) =>
        queryOptions({
            queryKey: keys.analyze(did),
            queryFn: (): AnalyzeSchemaResponse | null => null,
            staleTime: Infinity,
            enabled: !!did,
        }),
    unifySchema: (did?: string) =>
        queryOptions({
            queryKey: keys.unify(did),
            queryFn: (): UnifySchemaResponse | null => null,
            staleTime: Infinity,
            enabled: !!did,
        }),
    pangeaze: () =>
        queryOptions({
            queryKey: keys.pangeaze(),
            queryFn: (): PangeazeResponse | null => null,
            staleTime: Infinity,
        }),
    updatePangeaze: (did?: string) =>
        queryOptions({
            queryKey: keys.unify(did),
            queryFn: (): UpdatePangeazeResponse | null => null,
            staleTime: Infinity,
            enabled: !!did,
        }),
} as const;

export const mutations = {
    register: () =>
        mutationOptions({
            mutationKey: keys.register(),
            mutationFn: (payload: RegisterDataPayload) => registerData(payload),
        }),
    analyzeSchema: (queryClient: QueryClient) =>
        mutationOptions({
            mutationKey: keys.analyze(),
            mutationFn: (payload: AnalyzeSchemaPayload) => runAnalyzeSchema(queryClient, payload),
        }),
    unifySchema: (queryClient: QueryClient) =>
        mutationOptions({
            mutationKey: keys.unify(),
            mutationFn: (payload: UnifySchemaPayload) => runUnifySchema(queryClient, payload),
        }),
    pangeaze: (queryClient: QueryClient) =>
        mutationOptions({
            mutationKey: keys.pangeaze(),
            mutationFn: (payload: PangeazePayload) => runPangeaze(queryClient, payload),
        }),
    updatePangeaze: (queryClient: QueryClient) =>
        mutationOptions({
            mutationKey: keys.updatePangeaze(),
            mutationFn: (payload: UpdatePangeazePayload) => runUpdatePangeaze(queryClient, payload),
        }),
} as const;

async function runAnalyzeSchema(queryClient: QueryClient, payload: AnalyzeSchemaPayload, signal?: AbortSignal) {
    queryClient.setQueryData(keys.analyze(payload.did), null);

    const stream = await analyzeSchema(payload, signal);

    for await (const chunk of stream) {
        if (signal?.aborted) return;

        if (typeof chunk === "string") {
            console.error("Unexpected string chunk:", chunk);
            continue;
        }
        const data = chunk as AnalyzeSchemaResponse;

        queryClient.setQueryData(
            keys.analyze(payload.did),
            (old: Partial<AnalyzeSchemaResponse>) => ({...structuredClone(old), ...data})
        );
    }
}

async function runUnifySchema(queryClient: QueryClient, payload: UnifySchemaPayload, signal?: AbortSignal) {
    queryClient.setQueryData(keys.unify(payload.did), null);

    const stream = await unifySchema(payload, signal);

    for await (const chunk of stream) {
        if (signal?.aborted) return;

        if (typeof chunk === "string") {
            console.error("Unexpected string chunk:", chunk);
            continue;
        }
        const data = chunk as AnalyzeSchemaResponse;

        queryClient.setQueryData(
            keys.unify(payload.did),
            (old: Partial<UnifySchemaResponse>) => ({...structuredClone(old), ...data})
        );
    }
}

async function runPangeaze(queryClient: QueryClient, payload: PangeazePayload, signal?: AbortSignal): Promise<PangeazeResponse | null> {
    queryClient.setQueryData(keys.pangeaze(), null);

    const stream = await pangeaze(payload, signal);

    for await (const chunk of stream) {
        if (signal?.aborted) return null;

        if (typeof chunk === "string") {
            console.error("Unexpected string chunk:", chunk);
            continue;
        }
        const data = chunk as PangeazeResponse;

        queryClient.setQueryData(
            keys.pangeaze(),
            (old: Partial<PangeazeResponse>) => ({...structuredClone(old), ...data})
        );
    }

    return queryClient.getQueryData<PangeazeResponse>(keys.pangeaze()) ?? null;
}

async function runUpdatePangeaze(queryClient: QueryClient, payload: UpdatePangeazePayload, signal?: AbortSignal) {
    queryClient.setQueryData(keys.updatePangeaze(payload.did), null);

    const stream = await updatePangeaze(payload, signal);

    for await (const chunk of stream) {
        if (signal?.aborted) return;

        if (typeof chunk === "string") {
            console.error("Unexpected string chunk:", chunk);
            continue;
        }
        const data = chunk as UpdatePangeazeResponse;

        queryClient.setQueryData(
            keys.unify(payload.did),
            (old: Partial<UpdatePangeazeResponse>) => ({...structuredClone(old), ...data})
        );
    }
}
