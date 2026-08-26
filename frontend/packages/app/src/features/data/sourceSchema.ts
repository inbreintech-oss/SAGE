/** Data API v1.1 — sources[].sheets 공통 스키마 */

/** CSV는 시트 개념 없음 — 서버/API 기본 시트명 */
export const CSV_DEFAULT_SHEET_NAME = "sheet1";

export type DataSourceColumn = {
    name: string;
    type: string;
    selected: boolean;
};

export type DataSourceSheet = {
    name: string;
    columns: DataSourceColumn[];
};

export type DataSourceOptions = Record<string, string | boolean | number>;

export function fileSourceOptions(format: string): DataSourceOptions {
    if (isCsvFormat(format)) return { encoding: "utf-8" };
    return { header: true };
}

/** csv 여부 (file_type·path 기준) */
export function isCsvFormat(format: string, path?: string): boolean {
    const normalized = format.toLowerCase();
    if (normalized === "csv" || normalized === "text/csv") return true;
    return Boolean(path?.toLowerCase().endsWith(".csv"));
}

/**
 * API 송신용 시트명 — CSV는 항상 sheet1.
 * (구버전 default 등도 csv면 sheet1로 정규화)
 */
export function resolveApiSheetName(format: string, sheetName: string, path?: string): string {
    if (isCsvFormat(format, path)) return CSV_DEFAULT_SHEET_NAME;
    return sheetName;
}

/** API 수신·레거시 폴백 시트명 정규화 */
export function normalizeImportedSheetName(
    format: string | undefined,
    sheetName: string,
    path?: string,
): string {
    if (isCsvFormat(format ?? "", path)) return CSV_DEFAULT_SHEET_NAME;
    return sheetName;
}

export function mapDmColumnsToApiColumns(
    columns: { name: string; dtype: string; selected: boolean }[],
): DataSourceColumn[] {
    return columns.map(col => ({
        name: col.name,
        type: col.dtype,
        selected: col.selected,
    }));
}

/** API v1.1 sheets 우선, 구버전 flat columns 폴백 */
export function resolveSourceSheets(source: {
    sheets?: DataSourceSheet[];
    columns?: string[];
}): DataSourceSheet[] {
    if (source.sheets?.length) {
        return source.sheets.map(sheet => ({
            name: sheet.name,
            columns: sheet.columns.map(col => ({
                name: col.name,
                type: col.type,
                selected: col.selected,
            })),
        }));
    }

    if (source.columns?.length) {
        return [{
            name: CSV_DEFAULT_SHEET_NAME,
            columns: source.columns.map(name => ({
                name,
                type: "str",
                selected: true,
            })),
        }];
    }

    return [];
}

/** DB 소스 path — 서버 sources[] 1항목 식별 키 */
export function buildDbSourcePath(host: string, dbName: string, tableName: string): string {
    return `${host}/${dbName}/${tableName}`;
}
