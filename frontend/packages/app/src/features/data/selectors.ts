import type { SageData } from "./api";

/** 분석모델 목록에서 status=completed 항목만 추출 */
export function selectCompletedDataList(list: SageData[] | undefined): SageData[] {
    return (list ?? []).filter(m => m.status === "completed");
}
