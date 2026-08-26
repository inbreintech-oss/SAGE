import type {ApiItemResponse, ApiMutationResponse, Author} from "@/libs/types";
import {createGetQuery, FetchAPI} from "@/libs/apis/Utils.ts";

// Author 리스트 조회 요청 타입
export type authorGetListRequest = {
    searchText?: string;
};

// Author 리스트 조회 응답 타입
// TODO: API 응답 타입 일관성 문제 해결 필요 (item array가 item key에 반환)
export type authorGetListResponse = ApiItemResponse<Author>;

/**
 * POST /api/author/list
 * 권한 정보를 조회합니다.
 * @param {authorGetListRequest} request 권한 정보 요청 데이터
 * @returns {Promise<authorGetListResponse>} 조회된 권한 정보 리스트
 */
export async function authorGetList(request: authorGetListRequest): Promise<authorGetListResponse> {
    return await FetchAPI(createGetQuery("/api/author/list", request), "GET");
}

// Author 생성 요청 타입
export type authorCreateRequest = {
    authorName: string;
    companyAppId: number;
}

// Author 생성 응답 타입
export type authorCreateResponse = ApiItemResponse<Author>;

/**
 * POST /api/author/
 * 권한을 생성합니다.
 * @param {authorCreateRequest} data 권한 생성 요청 데이터
 * @returns {Promise<authorCreateResponse>} 생성된 권한 정보
 */
export async function authorCreate(data: authorCreateRequest): Promise<authorCreateResponse> {
    return await FetchAPI("/api/author/", "POST", {
        body: JSON.stringify(data)
    });
}

// Author 수정 요청 타입
export type authorUpdateRequest = {
    authorId: number;
    authorName: string;
}

// Author 수정 응답 타입
export type authorUpdateResponse = ApiItemResponse<Author>;

/**
 * POST /api/author/{authorId}
 * 권한을 수정합니다.
 * @param {number} authorId 수정 대상 Author ID
 * @param {authorUpdateRequest} data 권한 수정 요청 데이터
 * @returns {Promise<authorUpdateResponse>} 수정된 권한 정보
 */
export async function authorUpdate(authorId: number, data: authorUpdateRequest): Promise<authorUpdateResponse> {
    return await FetchAPI(`/api/author/${authorId}`, "PUT", {
        body: JSON.stringify(data)
    });
}

// Author 삭제 응답 타입
export type AuthorDeleteResponse = ApiMutationResponse;

/**
 * POST /api/author/delete
 * 권한을 삭제합니다.
 * @param {number} authorId 삭제 대상 Author ID
 * @returns {Promise<AuthorDeleteResponse>} 삭제된 권한 수
 */
export function authorDelete(authorId: number): Promise<AuthorDeleteResponse> {
    return FetchAPI(`/api/author/${authorId}`, "DELETE");
}

/**
 * TODO: Author-Menu API는 결정 후 추후 생성 필요
 */
