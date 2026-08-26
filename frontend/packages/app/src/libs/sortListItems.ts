import type { SageData } from "@/features/data";
import type { ReportListItem } from "@/features/report-management/reportListTypes";
import type { ToolListItem } from "@/libs/stores/toolManagement/types";

export function parseListSortTimestamp(value?: string | null): number {
    const trimmed = value?.trim();
    if (!trimmed) return 0;
    const parsed = Date.parse(trimmed);
    return Number.isFinite(parsed) ? parsed : 0;
}

function compareByCreatedAtThenNameDesc(
    createdAtA: string | undefined | null,
    createdAtB: string | undefined | null,
    nameA: string,
    nameB: string,
): number {
    const dateDiff = parseListSortTimestamp(createdAtB) - parseListSortTimestamp(createdAtA);
    if (dateDiff !== 0) return dateDiff;
    return nameB.localeCompare(nameA, "ko", { sensitivity: "base", numeric: true });
}

export function resolveReportListSortName(item: ReportListItem): string {
    return item.title?.trim()
        || item.description?.trim()
        || item.rid?.trim()
        || "";
}

/** 등록 도구 목록 — 생성일 ↓, 명(title) ↓ */
export function sortToolListItems(items: ToolListItem[]): ToolListItem[] {
    return [...items].sort((a, b) => compareByCreatedAtThenNameDesc(
        a.created_at,
        b.created_at,
        a.title?.trim() || a.tool_id,
        b.title?.trim() || b.tool_id,
    ));
}

/** 등록 보고서 목록 — 생성일 ↓, 명(title/description) ↓ */
export function sortReportListItems(items: ReportListItem[]): ReportListItem[] {
    return [...items].sort((a, b) => compareByCreatedAtThenNameDesc(
        a.created_at,
        b.created_at,
        resolveReportListSortName(a),
        resolveReportListSortName(b),
    ));
}

/** 등록 데이터모델 목록 — 생성일 ↓, 명(name) ↓ */
export function sortSageDataList(items: SageData[]): SageData[] {
    return [...items].sort((a, b) => compareByCreatedAtThenNameDesc(
        a.created_at,
        b.created_at,
        a.name?.trim() || a.did,
        b.name?.trim() || b.did,
    ));
}
