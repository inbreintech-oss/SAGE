import {getDummyData} from "@/features/Utils";
import type {ApiListResponse, Menu} from "@/libs/types";

/*****************************************************
 * GET: Get Menu List
 *****************************************************/

// Menu 리스트 조회 요청 타입
// export type GetMenuListRequest = {
//     companyAppId?: number;
//     search?: string;
// }

// Menu 리스트 조회 응답 타입
export type GetMenuListResponse = ApiListResponse<Menu[]>;

/**
 * GET /api/menu/list
 * Menu 리스트를 조회합니다.
 * 더미 Menu 목록을 반환합니다.
 * @returns {Promise<GetMenuListResponse>} 조회된 Menu 리스트
 */
export async function getMenuList(): Promise<GetMenuListResponse> {
    return await getDummyData(0, {
        items: menus,
        status: "ok",
    });
}

const getMenuDummy = (
    id: number,
    menuName: string,
    url: string | undefined,
    order?: number,
    parentId?: number,
): Menu => ({
    id: id,
    companyAppId: 1,
    korMenuName: menuName,
    url: url,
    level: parentId ? 2 : 1,
    displayOrder: order,
    parentId: parentId,
    useYn: true,
    createdAt: new Date(),
    createdBy: "",
    updatedAt: new Date(),
    updatedBy: "",
});

// Dummy Menu List -> FrontEnd로 이동
// ── 운영 메뉴 (사이드바 노출) ─────────────────────────────────────
//   /                          대시보드
//   /datamanagement            데이터 분석 모델
//   /report/reportmanagement   보고서
//   /report/reportlist         보고서 목록
//   /toolmanagement            도구(Tool)
// ── 폐기 대상 — AppRouter 라우트·파일만 보관, 메뉴 미연결 ─────────
const menus: Menu[] = [
    // ─── 1레벨 루트 메뉴 ──────────────────────────────────────────
    getMenuDummy(1,  "대시보드",            "/",                  1),
    getMenuDummy(2,  "데이터",              undefined,            2),
    getMenuDummy(7,  "핵심 자산 설정",      undefined,            3),

    // ─── 2레벨: "데이터" (parentId=2) ────────────────────────────
    getMenuDummy(4,  "데이터 분석 모델",    "/datamanagement",              1, 2),
    getMenuDummy(5,  "보고서",              "/report/reportmanagement",     2, 2),
    getMenuDummy(9,  "보고서 목록",         "/report/reportlist",           3, 2),

    // ─── 2레벨: "핵심 자산 설정" (parentId=7) ────────────────────
    getMenuDummy(8,  "도구(Tool)",          "/toolmanagement",              1, 7),
];
