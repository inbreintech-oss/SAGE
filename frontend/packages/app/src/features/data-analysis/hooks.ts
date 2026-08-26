import type {MutateOptions} from "@tanstack/react-query";
import {useMutation, useQuery, useQueryClient} from "@tanstack/react-query";
import {keys, mutations, queries} from "./queries";
import type {UploadDataPayload, UploadedFile,} from "./api";
import {uploadDataFile} from "./api";

export function useUploadData() {
    const queryClient = useQueryClient();

    const mutate = (payload: UploadDataPayload, options?: MutateOptions<UploadedFile, Error, UploadDataPayload>) => {
        const mutation = queryClient.getMutationCache().build(queryClient, {
            mutationKey: keys.upload(payload),
            mutationFn: () => uploadDataFile(payload),
        });

        mutation.execute(payload).then(
            (data) => options?.onSuccess?.(data, payload, undefined),
            (error) => options?.onError?.(error as Error, payload, undefined),
        );
    };

    return { upload: { mutate } };
}

export function useRegisterData() {
    const register = useMutation({
        ...mutations.register(),
    });

    return { register };
}

export function useAnalyzeSchema() {
    const queryClient = useQueryClient();

    const analyze = useMutation({
        ...mutations.analyzeSchema(queryClient),
    });
    const analyzeQuery = useQuery({
        ...queries.analyzeSchema(analyze.variables?.did),
    });

    return { analyze, analyzeQuery };
}

export function useUnifySchema() {
    const queryClient = useQueryClient();

    const unify = useMutation({
        ...mutations.unifySchema(queryClient),
    });
    const unifyQuery = useQuery({
        ...queries.unifySchema(unify.variables?.did),
    });

    return { unify, unifyQuery };
}

export function usePangeaze() {
    const queryClient = useQueryClient();

    const pangeaze = useMutation({
        ...mutations.pangeaze(queryClient),
    });
    const pangeazeQuery = useQuery({
        ...queries.pangeaze(),
    });

    return { pangeaze, pangeazeQuery };
}

export function useUpdatePangeaze() {
    const queryClient = useQueryClient();

    const update = useMutation({
        ...mutations.updatePangeaze(queryClient),
    });
    const updateQuery = useQuery({
        ...queries.updatePangeaze(update.variables?.did),
    });

    return { update, updateQuery };
}