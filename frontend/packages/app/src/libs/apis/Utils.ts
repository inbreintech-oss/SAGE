import type {IResponseMaster} from "@/libs/types";

/**
 * React Query 에러 핸들링을 위한 기본 Error 클래스입니다.
 */
export class FetchAPIError extends Error {
    data?: IResponseMaster;

    constructor(data?: IResponseMaster) {
        super();
        this.data = data;
    }
}

/**
 *  * API 요청을 위한 Fetch Wrapper 입니다.
 * @param {string} path 요청 경로
 * @param {string} method 요청 메서드
 * @param {RequestInit} requestInit Request Options
 * @Template T 응답 데이터 타입
 * @returns {Promise<T>} 응답 데이터
 * @constructor
 */
export async function FetchAPI<T>(path: string, method: string, requestInit?: RequestInit): Promise<T> {
    const response: Response = await fetch(path, {
        method: method,
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        ...requestInit,
    });

    if (!response.ok) {
        let body = undefined;

        try {
            body = await response.json();
        } catch {
            // ignore
        }

        // // 401 에러 시 userInfo 쿼리 invalidate 및 store logout
        // if (response.status === 401) {
        //     queryClient.invalidateQueries({ queryKey: userKeys.userInfo() });
        // }

        throw new FetchAPIError(body);
    }

    return response.json();
}

/**
 * GET 쿼리 생성 유틸입니다.
 * @param {string} path 요청 경로
 * @param {Record<string, string>} params 쿼리 파라미터
 * @returns {string} 생성된 GET 쿼리 문자열
 */
export function createGetQuery(path: string, params: Record<string, unknown>): string {
    const keys = Object.keys(params) as (keyof typeof params)[];
    const query = keys
        .filter(key => params[key] !== undefined && params[key] !== null)
        .map((key) => `${encodeURIComponent(key)}=${encodeURIComponent(String(params[key]))}`)
        .join("&");
    return path + (!path.endsWith("?") ? "?" : "") + query;
}

/**
 * Sleep 유틸입니다.
 * @param {number} ms 지연 시간 (밀리초)
 */
export async function sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * 더미 데이터를 반환하는 유틸 함수입니다.
 * @template T 반환할 데이터 타입
 * @param {number} ms 지연 시간 (밀리초)
 * @param {T} data 더미 데이터
 * @returns {Promise<T>}
 */
export async function getDummyData<T>(ms: number, data: T): Promise<T> {
    await sleep(ms);
    return data;
}
