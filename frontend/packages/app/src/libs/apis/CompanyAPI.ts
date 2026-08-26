import {FetchAPI, createGetQuery} from "./Utils";
import type {ApiItemResponse, ApiMutationResponse, Company} from "@/libs/types";

// Company 리스트 조회 요청 타입
export type GetCompanyListRequest = {
    searchText?: string;
}

// Company 리스트 조회 응답 타입
// TODO: API 응답 타입 일관성 문제 해결 필요 (item array가 item key에 반환)
export type GetCompanyListResponse = ApiItemResponse<Company[]>;

/**
 * GET /api/company/list
 * Company 리스트를 조회합니다.
 * @param {GetCompanyListRequest} request Company 리스트 요청 데이터
 * @returns {Promise<GetCompanyListResponse>} 조회된 Company 리스트
 */
export async function getCompanyList(request: GetCompanyListRequest): Promise<GetCompanyListResponse> {
    return await FetchAPI(
        createGetQuery("/api/company/list", request),
        "GET"
    );
}

// Company 생성 요청 타입
export type CreateCompanyRequest = {
    korCompanyName: string;
    engCompanyName: string;
    chiCompanyName: string;
    vieCompanyName: string;
    jpnCompanyName: string;
    startDate: string;
    endDate: string;
    useYn: boolean;
}

// Company 생성 응답 타입
export type CreateCompanyResponse = ApiItemResponse<Company>;

/**
 * POST /api/company/create
 * Company를 생성합니다.
 * @param {CreateCompanyRequest} request Company 생성 요청 데이터
 * @returns {Promise<CreateCompanyResponse>} 생성된 Company 정보
 */
export async function createCompany(request: CreateCompanyRequest): Promise<CreateCompanyResponse> {
    return await FetchAPI(
        "/api/company/create",
        "POST",
        {
            body: JSON.stringify(request)
        }
    );
}

// Company 수정 요청 타입
export type UpdateCompanyRequest = {
    korCompanyName: string;
    engCompanyName: string;
    chiCompanyName: string;
    vieCompanyName: string;
    jpnCompanyName: string;
    startDate: string;
    endDate: string;
    useYn: boolean;
}

// Company 수정 응답 타입
export type UpdateCompanyResponse = ApiItemResponse<Company>;

/**
 * PUT /api/company/{companyId}
 * Company 정보를 수정합니다.
 * @param {number} companyId 수정 대상 Company ID
 * @param {UpdateCompanyRequest} request Company 수정 요청 데이터
 * @returns {Promise<UpdateCompanyResponse>} 수정된 Company 정보
 */
export async function updateCompany(companyId: number, request: UpdateCompanyRequest): Promise<UpdateCompanyResponse> {
    return await FetchAPI(
        `/api/company/${companyId}`,
        "PUT",
        {
            body: JSON.stringify(request)
        }
    );
}

// Company 삭제 응답 타입
export type deleteCompanyResponse = ApiMutationResponse;

/**
 * DELETE /api/company/{companyId}
 * Company를 삭제합니다.
 * @param {number} companyId 삭제 대상 Company ID
 * @returns {Promise<deleteCompanyResponse>} 삭제 결과
 */
export async function deleteCompany(companyId: number): Promise<deleteCompanyResponse> {
    return await FetchAPI(
        `/api/company/${companyId}`,
        "DELETE"
    );
}
