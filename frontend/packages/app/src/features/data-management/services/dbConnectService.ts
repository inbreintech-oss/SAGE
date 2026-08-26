import type { DbColumnMeta, DbForm } from "@/libs/stores/dataManagement/types";

export type DbVerifyResult = {
    columns: DbColumnMeta[];
};

const STUB_COLUMNS: DbColumnMeta[] = [
    { name: "id", type: "integer", selected: true },
    { name: "symbol", type: "varchar", selected: true },
    { name: "trade_date", type: "date", selected: true },
    { name: "close_price", type: "numeric", selected: true },
    { name: "volume", type: "bigint", selected: true },
];

/**
 * P5에서 실 API 연동 예정.
 * 현재는 연결 검증 UI 흐름 확인용 stub 응답을 반환합니다.
 */
export async function verifyDbConnection(_form: DbForm): Promise<DbVerifyResult> {
    await new Promise(resolve => setTimeout(resolve, 600));
    return {
        columns: STUB_COLUMNS.map(col => ({ ...col })),
    };
}
