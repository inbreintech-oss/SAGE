import {
    createControl,
    type CreateControlRequest,
    deleteControl,
    deleteControlBulk,
    type DeleteControlBulkRequest,
    type DeleteControlRequest,
    getControlById,
    type GetControlByIdRequest,
    getControlList,
    type GetControlListRequest,
    updateControl,
    type UpdateControlRequest
} from "@/features/control/api.ts";
import {mutationOptions, queryOptions} from "@tanstack/react-query";

export const keys = {
    all: () => ["control"],
    list: (request: GetControlListRequest) => [...keys.all(), request.companyAppId, "list", request.searchText],
    item: (request: GetControlByIdRequest)=> [...keys.all(), request.id]
}

export const queries = {
    getControlList: (request: GetControlListRequest) => queryOptions({
        queryKey: keys.list(request),
        queryFn: () => getControlList(request),
    }),
    getControlById: (request: GetControlByIdRequest)=> queryOptions({
        queryKey: keys.item(request),
        queryFn: () => getControlById(request)
    }),
}

export const mutations = {
    createControl: () => mutationOptions({
        mutationFn: (request: CreateControlRequest) => createControl(request)
    }),
    updateControl: () => mutationOptions({
        mutationFn: (request: UpdateControlRequest) => updateControl(request)
    }),
    deleteControl: () => mutationOptions({
        mutationFn: (request: DeleteControlRequest) => deleteControl(request)
    }),
    deleteControlBulk: () => mutationOptions({
        mutationFn: (request: DeleteControlBulkRequest) => deleteControlBulk(request)
    })
}
