import type {ApiItemResponse, ApiListResponse, ApiMutationResponse, Application} from "@/libs/types";
import {createGetQuery, FetchAPI} from "@/libs/apis/Utils.ts";

// Application List 요청 타입
export type GetApplicationListRequest = {
    searchText: string;
};

// Application List 응답 타입
export type GetApplicationListResponse = ApiListResponse<Application[]>;

/**
 * GET /api/application/list
 * Application 리스트를 조회합니다.
 * @param {GetApplicationListRequest} request Application 리스트 요청 데이터
 * @returns {Promise<GetApplicationListResponse>} 조회된 Application 리스트
 */
export async function getApplicationList(request: GetApplicationListRequest): Promise<GetApplicationListResponse> {
    return await FetchAPI(
        "/api/application/list",
        "GET",
        {
            body: JSON.stringify(request)
        }
    );
}

// Application 추가 요청 타입
export type CreateApplicationRequest = {
    appName: string;
    description: string;
}

// Application 추가 응답 타입
export type CreateApplicationResponse = ApiItemResponse<Application>;

/**
 * POST /api/application/
 * Application을 생성합니다.
 * @param {CreateApplicationRequest} request Application 생성 요청 데이터
 * @returns {Promise<CreateApplicationResponse>} 생성된 Application 정보
 */
export async function createApplication(request: CreateApplicationRequest): Promise<CreateApplicationResponse> {
    return await FetchAPI("/api/application/", "POST", {
        body: JSON.stringify(request)
    });
}

// Application 수정 요청 타입
export type UpdateApplicationRequest = {
    appName: string;
    description: string;
}

// Application 수정 응답 타입
export type UpdateApplicationResponse = ApiItemResponse<Application>;

/**
 * PUT /api/application/{id}
 * Application을 수정합니다.
 * @param {number} id Application ID
 * @param {UpdateApplicationRequest} request Application 수정 요청 데이터
 * @returns {Promise<UpdateApplicationResponse>} 수정된 Application 정보
 */
export async function updateApplication(id: number, request: UpdateApplicationRequest): Promise<UpdateApplicationResponse> {
    return await FetchAPI(`/api/application/${id}`, "PUT", {
        body: JSON.stringify(request)
    });
}

// Application 삭제 응답 타입
export type DeleteApplicationResponse = ApiMutationResponse;

/**
 * DELETE /api/application/{id}
 * Application을 삭제합니다.
 * @param {number} id Application ID
 * @returns {Promise<DeleteApplicationResponse>} 삭제된 Application 정보
 */
export async function deleteApplication(id: number): Promise<DeleteApplicationResponse> {
    return await FetchAPI(`/api/application/${id}`, "DELETE");
}

// Application에 연결 된 Company List 요청 타입
export type GetApplicationCompanyListRequest = {
    appId: number;
}

// Application에 연결 된 Company List 응답 타입
export type GetApplicationCompanyListResponse = ApiListResponse<Application[]>;

/**
 * GET /api/application/company/list
 * Application-Company 정보를 조회합니다.
 * @param {GetApplicationCompanyListRequest} request
 * @returns {Promise<GetApplicationCompanyListResponse>}
 */
export async function getApplicationCompanyList(request: GetApplicationCompanyListRequest): Promise<GetApplicationCompanyListResponse> {
    return await FetchAPI(
        createGetQuery("/api/application/company/list", {appId: request.appId.toString()}),
        "GET"
    );
}

// Application Company 등록 요청 타입
export type CreateApplicationCompanyRequest = {
    appId: number;
    companyId: number;
    korAppName?: string;
    engAppName?: string;
    chiAppName?: string;
    vieAppName?: string;
    jpnAppName?: string;
}

// Application Company 등록 응답 타입
export type CreateApplicationCompanyResponse = ApiItemResponse<Application>;

/**
 * POST /api/application/company
 * Application-Company 정보를 등록합니다.
 * @param {CreateApplicationCompanyRequest} request
 * @returns {Promise<CreateApplicationCompanyResponse>}
 */
export async function createApplicationCompany(request: CreateApplicationCompanyRequest): Promise<CreateApplicationCompanyResponse> {
    return await FetchAPI("/api/application/company", "POST", {
        body: JSON.stringify(request)
    });
}

// Application Company 수정 요청 타입
export type UpdateApplicationCompanyRequest = {
    appId: number;
    companyId: number;
    korAppName?: string;
    engAppName?: string;
    chiAppName?: string;
    vieAppName?: string;
    jpnAppName?: string;
}

// Application Company 수정 응답 타입
export type UpdateApplicationCompanyResponse = ApiItemResponse<Application>;

/**
 * PUT /api/application/company/{id}
 * Application-Company 정보를 수정합니다.
 * @param {number} id Company-Application ID
 * @param {UpdateApplicationCompanyRequest} request Application Company 수정 요청 데이터
 * @returns {Promise<UpdateApplicationCompanyResponse>} 수정된 Application-Company 정보
 */
export async function updateApplicationCompany(id: number, request: UpdateApplicationCompanyRequest): Promise<UpdateApplicationCompanyResponse> {
    return await FetchAPI(`/api/application/company/${id}`, "PUT", {
        body: JSON.stringify(request)
    });
}

// Application Company 삭제 응답 타입
export type DeleteApplicationCompanyResponse = ApiMutationResponse;

/**
 * DELETE /api/application/company/{id}
 * Application-Company 연결을 삭제합니다.
 * @param {number} id Company-Application ID
 * @returns {Promise<DeleteApplicationCompanyResponse>} 삭제 된 행 수
 */
export async function deleteApplicationCompany(id: number): Promise<DeleteApplicationCompanyResponse> {
    return await FetchAPI(`/api/application/company/${id}`, "DELETE");
}
