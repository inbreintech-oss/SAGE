import {createGetQuery, FetchAPI} from "./Utils";
import {type IUserInfo, type IUserFavorite, type IResponseMaster, type IAuthor} from "@/libs/types";
import {createHash} from "@/libs/Utils.ts";

/**
 * 사용자 생성 Request 인터페이스
 */
export interface IUserCreateRequest {
    userId: string;
    companyId: number;
    email: string;
    firstName: string;
    lastName: string;
    userPassword: string;
    personalizationAnswers: [
        {
            questionId: number;
            answer: string;
        }
    ]
}

/**
 * 사용자 생성 Response 인터페이스
 */
export interface IUserCreateResponse extends IResponseMaster {
    item: IUserInfo | null;
}

/**
 * POST /api/user/create
 * 사용자를 생성합니다.
 * @param {IUserCreateRequest} data
 * @returns {Promise<IUserCreateResponse>}
 */
export async function postUserCreate(data: IUserCreateRequest): Promise<IUserCreateResponse> {
    return await FetchAPI("/api/user/create", "POST", {
        body: JSON.stringify(data)
    });
}

/**
 * 사용자 정보 조회 Response 인터페이스
 */
export interface IUserInfoResponse extends IResponseMaster {
    item: IUserInfo | null;
}

/**
 * POST /api/user/info
 * 사용자 정보를 조회합니다.
 * @returns {Promise<IUserInfoResponse>}
 */
export async function postUserInfo(): Promise<IUserInfoResponse> {
    return await FetchAPI("/api/user/info", "POST");
}

/**
 * 사용자 로그인 Request 인터페이스
 */
export interface ILoginRequest {
    userId: string;
    userPassword: string;
}

/**
 * POST /api/user/login
 * 로그인 요청을 처리합니다.
 * @param {ILoginRequest} data
 * @returns {Promise<IResponseMaster>}
 */
export async function postLogin(data: ILoginRequest): Promise<IResponseMaster> {
    const encryptedData: ILoginRequest = {
        userId: data.userId,
        userPassword: await createHash(data.userPassword)
    }

    return await FetchAPI<IResponseMaster>("/api/user/login", "POST", {
        body: JSON.stringify(encryptedData)
    });
}

/**
 * 사용자 로그아웃 Response 인터페이스
 */
export interface ILogoutResponse extends IResponseMaster {
    message?: string;
}

/**
 * POST /api/user/logout
 * 사용자 로그아웃을 처리합니다.
 * @returns {Promise<ILogoutResponse>}
 */
export async function postLogout(): Promise<ILogoutResponse> {
    return await FetchAPI("/api/user/logout", "POST");
}

/**
 * 사용자 즐겨찾기 생성 Request 인터페이스
 */
export interface IFavoriteCreateRequest {
    userId: string;
    menuId: number;
    displayOrder: number;
}

/**
 * 사용자 즐겨찾기 생성 Response 인터페이스
 */
export interface IFavoriteCreateResponse extends IResponseMaster {
    item: IUserFavorite | null;
}

/**
 * POST /api/user/favorite
 * 사용자 즐겨찾기를 생성합니다.
 * @param {IFavoriteCreateRequest} data
 * @returns {Promise<IFavoriteCreateResponse>}
 */
export async function postFavoriteCreate(data: IFavoriteCreateRequest): Promise<IFavoriteCreateResponse> {
    return await FetchAPI("/api/user/favorite/create", "POST", {
        body: JSON.stringify(data)
    });
}

/**
 * 사용자 즐겨찾기 삭제 Response 인터페이스
 */
export interface IFavoriteDelRequest {
    userId: string;
    menuId: number;
}

/**
 * 사용자 즐겨찾기 삭제 Response 인터페이스
 */
export interface IFavoriteDelResponse extends IResponseMaster {
    count: number;
}

/**
 * POST /api/user/favoriteDel
 * 사용자 즐겨찾기를 삭제합니다.
 * @param {IFavoriteDelRequest} data
 * @returns {Promise<IFavoriteDelResponse>}
 */
export async function postFavoriteDel(data: IFavoriteDelRequest): Promise<IFavoriteDelResponse> {
    return await FetchAPI(
        createGetQuery("/api/user/favorite/delete", {
            userId: data.userId,
            menuId: data.menuId.toString()
        }),
        "DELETE"
    );
}

/**
 * 사용자 즐겨찾기 정보 Response 인터페이스
 */
export interface IFavoriteInfoResponse extends IResponseMaster {
    item: IUserFavorite[];
}

/**
 * POST /api/user/favoriteInfo
 * 사용자 즐겨찾기 정보를 조회합니다.
 * @returns {Promise<IFavoriteInfoResponse>}
 */
export async function postFavoriteInfo(): Promise<IFavoriteInfoResponse> {
    return await FetchAPI("/api/user/favorite/list", "GET");
}

// TODO: 이후 로그인 유저 사용하도록 변경 필요
export interface IUserAuthorRoleInfoRequest {
    userId: string;
}

/**
 * 사용자 권한 정보 Response 인터페이스
 */
export interface IUserAuthorRoleInfoResponse extends IResponseMaster {
    item: IAuthor[];
}

/**
 * POST /api/user/author-role/info
 * 사용자 권한 정보를 조회합니다.
 * @param {IUserAuthorRoleInfoRequest} data 요청 데이터
 * @returns {Promise<IUserAuthorRoleInfoResponse>} 사용자 권한 정보
 */
export async function postUserAuthorRoleInfo(data: IUserAuthorRoleInfoRequest): Promise<IUserAuthorRoleInfoResponse> {
    return await FetchAPI("/api/user/author-role/info", "POST", {
        body: JSON.stringify(data)
    });
}
