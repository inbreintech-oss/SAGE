import {createGetQuery, FetchAPI} from "@/libs/apis/Utils.ts";
import type {ApiListResponse, Menu} from "@/libs/types";

export type getMenuListSearchQuery = {
    companyAppId?: number;
    search?: string;
}

// Menu 목록 응답 타입
export type getMenuListResponse = ApiListResponse<Menu[]>;

/**
 * GET /api/menu/list
 * 메뉴 목록을 조회합니다.
 * @param {getMenuListSearchQuery} query Menu 목록 검색 쿼리
 * @returns {Promise<getMenuListResponse>} 조회된 Menu 목록
 */
export async function getList(query?: getMenuListSearchQuery): Promise<getMenuListResponse> {
    return await FetchAPI(
        createGetQuery("/api/menu/list", query || {}),
        "GET"
    );
}
