import type {ApiItemResponse, ApiListResponse, ApiMutationResponse} from "@/libs/types";
import {createGetQuery, FetchAPI} from "@/features/Utils.ts";

export type Control = {
    id: number;
    companyAppId: number;
    controlType: string;
    controlTypeName?: string;
    korControlName: string;
    engControlName: string;
    vieControlName?: string;
    chiControlName?: string;
    jpnControlName?: string;
    displayOrder?: number;
    useYn?: boolean;
    createdBy?: string;
    createdAt?: string;
    updatedBy?: string;
    updatedAt?: string;
}

export type GetControlListRequest = {
    companyAppId: number;
    searchText?: string;
}

export type GetControlListResponse = ApiListResponse<Control[]>;

export async function getControlList(request: GetControlListRequest): Promise<GetControlListResponse> {
    return FetchAPI(
        createGetQuery("/api/control/list", request),
        "GET"
    )
}

export type GetControlByIdRequest = {
    id: number;
}

export type GetControlByIdResponse = ApiItemResponse<Control>;

export async function getControlById({id}: GetControlByIdRequest): Promise<GetControlByIdResponse> {
    return FetchAPI(
        `/api/control/${id}`,
        "GET"
    )
}

export type CreateControlRequest = {
    companyAppId: number;
    controlType: string;
    korControlName: string;
    engControlName: string;
    vieControlName?: string;
    chiControlName?: string;
    jpnControlName?: string;
    displayOrder?: number;
    useYn?: boolean;
}

export type CreateControlResponse = ApiItemResponse<Control>;

export async function createControl(request: CreateControlRequest): Promise<CreateControlResponse> {
    return FetchAPI(
        "/api/control",
        "POST",
        {
            body: JSON.stringify(request)
        }
    )
}

export type UpdateControlPayload = {
    companyAppId: number;
    controlType: string;
    korControlName: string;
    engControlName: string;
    vieControlName?: string;
    chiControlName?: string;
    jpnControlName?: string;
    displayOrder?: number;
    useYn?: boolean;
}

export type UpdateControlRequest = {
    id: number;
    payload: UpdateControlPayload;
}

export type UpdateControlResponse = ApiItemResponse<Control>;

export async function updateControl({id, payload}: UpdateControlRequest): Promise<UpdateControlResponse> {
    return FetchAPI(
        `/api/control/${id}`,
        "PUT",
        {
            body: JSON.stringify(payload)
        }
    )
}

export type DeleteControlRequest = {
    id: number;
}

export type DeleteControlResponse = ApiMutationResponse;

export async function deleteControl({id}: DeleteControlRequest): Promise<DeleteControlResponse> {
    return FetchAPI(
        `/api/control/${id}`,
        "DELETE"
    )
}

export type DeleteControlBulkRequest = {
    ids: number[];
}

export type DeleteControlBulkResponse = ApiMutationResponse;

export async function deleteControlBulk(request: DeleteControlBulkRequest): Promise<DeleteControlBulkResponse> {
    return FetchAPI(
        createGetQuery("/api/control/bulk/delete", request),
        "DELETE"
    )
}
