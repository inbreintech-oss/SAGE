import {type MutationOptions, useMutation, useQuery, useQueryClient} from "@tanstack/react-query";
import type {
    CreateControlRequest, CreateControlResponse,
    DeleteControlBulkRequest, DeleteControlBulkResponse, DeleteControlRequest,
    DeleteControlResponse, GetControlByIdRequest, GetControlListRequest, UpdateControlRequest,
    UpdateControlResponse
} from "./api";
import {keys, mutations, queries} from "./queries";
import type {FetchAPIError} from "@/features/Utils.ts";

export function useControlList(request: GetControlListRequest) {
    return useQuery({
        ...queries.getControlList(request),
        enabled: request.companyAppId != null && request.companyAppId >= 0
    })
}

export function useGetControlById(request: GetControlByIdRequest) {
    return useQuery({
        ...queries.getControlById(request),
        enabled: request.id >= 0
    })
}

export function useCreateControl(options?: MutationOptions<
    CreateControlResponse,
    FetchAPIError,
    CreateControlRequest
>) {
    const queryClient = useQueryClient();

    return useMutation({
        ...mutations.createControl(),
        ...options,
        onSuccess: async (data, variables, context) => {
            options?.onSuccess?.(data, variables, context);
            await queryClient.invalidateQueries({
                queryKey: keys.all()
            })
        }
    })
}

export function useUpdateControl(options?: MutationOptions<
    UpdateControlResponse,
    FetchAPIError,
    UpdateControlRequest
>) {
    const queryClient = useQueryClient();

    return useMutation({
        ...mutations.updateControl(),
        ...options,
        onSuccess: async (data, variables, context) => {
            options?.onSuccess?.(data, variables, context);
            await queryClient.invalidateQueries({
                queryKey: keys.all()
            })
        }
    })
}

export function useDeleteControl(options?: MutationOptions<
    DeleteControlResponse,
    FetchAPIError,
    DeleteControlRequest
>) {
    const queryClient = useQueryClient();

    return useMutation({
        ...mutations.deleteControl(),
        ...options,
        onSuccess: async (data, variables, context) => {
            options?.onSuccess?.(data, variables, context);
            await queryClient.invalidateQueries({
                queryKey: keys.all()
            })
        }
    })
}

export function useDeleteControlBulk(options?: MutationOptions<
    DeleteControlBulkResponse,
    FetchAPIError,
    DeleteControlBulkRequest
>) {
    const queryClient = useQueryClient();

    return useMutation({
        ...mutations.deleteControlBulk(),
        ...options,
        onSuccess: async (data, variables, context) => {
            options?.onSuccess?.(data, variables, context);
            await queryClient.invalidateQueries({
                queryKey: keys.all()
            })
        }
    })
}
