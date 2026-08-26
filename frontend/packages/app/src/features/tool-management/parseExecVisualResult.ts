import type { VisualResult } from "@/libs/stores/toolManagement/types";

/** 표에서 제외 — RAW JSON에는 유지 */
const EXEC_RESULT_META_KEYS = new Set(["success", "msg_cd", "msg1", "raw"]);

const ARRAY_ROW_KEYS = [
    "data",
    "rows",
    "raw",
    "output",
    "output1",
    "output2",
    "items",
    "records",
    "list",
    "results",
] as const;

const TOOL_RESULT_FIELD_LABELS: Record<string, string> = {
    stac_yymm: "결산년월",
    grs: "매출총이익률(%)",
    bsop_prfi_inrt: "영업이익증가율(%)",
    ntin_inrt: "순이익증가율(%)",
    roe_val: "ROE(%)",
    roa: "ROA(%)",
    eps: "EPS",
    sps: "SPS",
    bps: "BPS",
    rsrv_rate: "유보율(%)",
    lblt_rate: "부채비율(%)",
    sale_totl_rate: "매출총이익률(%)",
    bsop_prfi_rate: "영업이익률(%)",
    ntin_rate: "순이익률(%)",
    sale_account: "매출액",
    thtr_ntin: "당기순이익",
    stock_code: "종목코드",
    hts_kor_isnm: "종목명",
    stck_prpr: "현재가",
    prdy_vrss: "전일대비",
    prdy_ctrt: "등락률",
};

function isRecord(value: unknown): value is Record<string, unknown> {
    return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isObjectRow(value: unknown): value is Record<string, unknown> {
    return isRecord(value);
}

function isRowArray(value: unknown): value is Record<string, unknown>[] {
    return Array.isArray(value) && value.length > 0 && value.every(isObjectRow);
}

function formatCellValue(value: unknown): string {
    if (value === null || value === undefined) return "";
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
}

function collectDatasetHeaders(rows: Record<string, unknown>[]): string[] {
    const headers = new Set<string>();
    for (const row of rows) {
        for (const key of Object.keys(row)) headers.add(key);
    }
    return Array.from(headers);
}

function toDataset(rows: Record<string, unknown>[]): VisualResult {
    if (rows.length === 0) {
        return { type: "empty", message: "데이터셋이 비어 있습니다." };
    }

    const headers = collectDatasetHeaders(rows);
    const tableRows = rows.map(row => {
        const normalized: Record<string, unknown> = {};
        for (const header of headers) {
            normalized[header] = formatCellValue(row[header]);
        }
        return normalized;
    });

    return { type: "dataset", tableHeaders: headers, tableRows };
}

function dictToKvDataset(source: Record<string, unknown>): VisualResult | null {
    const rows = Object.entries(source)
        .filter(([key, value]) => {
            if (EXEC_RESULT_META_KEYS.has(key)) return false;
            return value !== undefined;
        })
        .map(([key, value]) => ({
            항목: TOOL_RESULT_FIELD_LABELS[key] ?? key,
            값: formatCellValue(value),
        }));

    if (rows.length === 0) return null;

    return {
        type: "dataset",
        tableHeaders: ["항목", "값"],
        tableRows: rows,
    };
}

function omitMetaEntries(obj: Record<string, unknown>): Record<string, unknown> {
    return Object.fromEntries(
        Object.entries(obj).filter(([key]) => !EXEC_RESULT_META_KEYS.has(key)),
    );
}

function isFormulaCandidate(obj: Record<string, unknown>): boolean {
    const responseType = String(obj.response_type ?? "").toLowerCase();
    if (responseType === "formula") return true;
    if (obj.latex || obj.formula) return true;
    return String(obj.type ?? "").toLowerCase() === "formula";
}

function findNestedTableRows(obj: Record<string, unknown>): Record<string, unknown>[] | null {
    if (isRecord(obj.data)) {
        for (const value of Object.values(obj.data)) {
            if (
                isRecord(value)
                && String(value.type ?? "").toLowerCase() === "table"
                && Array.isArray(value.value)
                && value.value.length > 0
            ) {
                const rows = value.value.filter(isObjectRow);
                if (rows.length > 0) return rows;
            }
        }

        const fromData = findArrayRowsInRecord(obj.data, 1);
        if (fromData) return fromData;
    }

    return null;
}

function findArrayRowsInRecord(obj: Record<string, unknown>, depth: number): Record<string, unknown>[] | null {
    if (depth > 4) return null;

    for (const key of ARRAY_ROW_KEYS) {
        const candidate = obj[key];
        if (isRowArray(candidate)) return candidate;
    }

    for (const value of Object.values(obj)) {
        if (isRowArray(value)) return value;
        if (isRecord(value)) {
            const nested = findArrayRowsInRecord(value, depth + 1);
            if (nested) return nested;
        }
    }

    return null;
}

function findArrayRows(obj: Record<string, unknown>): Record<string, unknown>[] | null {
    if (Array.isArray(obj.data) && obj.data.length > 0) {
        const rows = obj.data.filter(isObjectRow);
        if (rows.length > 0) return rows;
    }

    if (Array.isArray(obj.rows) && obj.rows.length > 0) {
        const rows = obj.rows.filter(isObjectRow);
        if (rows.length > 0) return rows;
    }

    const nestedTable = findNestedTableRows(obj);
    if (nestedTable) return nestedTable;

    return findArrayRowsInRecord(obj, 0);
}

function parseResultNode(result: unknown, visited: Set<unknown>): VisualResult | null {
    if (result === null || result === undefined) return null;

    if (typeof result === "string") {
        const trimmed = result.trim();
        if (!trimmed) return null;
        try {
            const parsed = JSON.parse(trimmed) as unknown;
            if (isRecord(parsed)) return parseExecVisualResultInner(parsed, visited);
        } catch {
            return { type: "empty", message: trimmed };
        }
        return null;
    }

    if (isRecord(result)) {
        return parseExecVisualResultInner(result, visited);
    }

    return null;
}

function countSourceFields(value: unknown, depth = 0): number {
    if (depth > 5 || value === null || value === undefined) return 0;

    if (Array.isArray(value)) {
        if (value.length === 0) return 0;
        if (value.every(isObjectRow)) {
            return value.reduce((sum, row) => sum + Object.keys(row).length, 0);
        }
        return value.length;
    }

    if (!isRecord(value)) return 1;

    let count = 0;
    for (const [key, child] of Object.entries(value)) {
        if (EXEC_RESULT_META_KEYS.has(key)) continue;
        if (key === "raw" && isRecord(child) && !Array.isArray(child)) {
            count += countSourceFields(child, depth + 1);
            continue;
        }
        if (key === "raw" && isRowArray(child)) {
            count += countSourceFields(child, depth + 1);
            continue;
        }
        if (isRecord(child) || Array.isArray(child)) {
            count += countSourceFields(child, depth + 1);
        } else if (child !== undefined) {
            count += 1;
        }
    }
    return count;
}

function countDisplayedFields(visual: VisualResult): number {
    if (visual.type !== "dataset" || !visual.tableRows?.length || !visual.tableHeaders?.length) {
        return 0;
    }

    if (visual.tableHeaders.length === 2 && visual.tableHeaders[0] === "항목") {
        return visual.tableRows.length;
    }

    return visual.tableRows.length * visual.tableHeaders.length;
}

function genericFlattenFallback(obj: Record<string, unknown>): VisualResult | null {
    if (isRecord(obj.result)) {
        const fromResult = genericFlattenFallback(obj.result);
        if (fromResult) return fromResult;
    }

    if (typeof obj.result === "string") {
        const parsed = parseResultNode(obj.result, new Set());
        if (parsed && parsed.type === "dataset") return parsed;
    }

    const arrayRows = findArrayRows(obj);
    if (arrayRows) return toDataset(arrayRows);

    if (isRecord(obj.raw) && !Array.isArray(obj.raw)) {
        const fromRaw = dictToKvDataset(obj.raw);
        if (fromRaw) return fromRaw;
    }

    const merged: Record<string, unknown> = { ...omitMetaEntries(obj) };
    if (isRecord(obj.raw) && !Array.isArray(obj.raw)) {
        for (const [key, value] of Object.entries(obj.raw)) {
            if (!(key in merged)) merged[key] = value;
        }
    }

    return dictToKvDataset(merged);
}

function parseExecVisualResultInner(obj: Record<string, unknown>, visited: Set<unknown>): VisualResult {
    if (visited.has(obj)) {
        return { type: "empty", message: "순환 참조가 감지되었습니다." };
    }
    visited.add(obj);

    if (isFormulaCandidate(obj)) {
        return {
            type: "formula",
            latex: String(obj.latex ?? obj.formula ?? obj.content ?? ""),
        };
    }

    const responseType = String(obj.response_type ?? "").toLowerCase();
    if (responseType === "dataset") {
        const rows = findArrayRows(obj);
        if (rows) return toDataset(rows);
    }

    const arrayRows = findArrayRows(obj);
    if (arrayRows) return toDataset(arrayRows);

    if (isRecord(obj.raw) && !Array.isArray(obj.raw)) {
        const fromRaw = dictToKvDataset(obj.raw);
        if (fromRaw) return fromRaw;
    }

    if (obj.result !== undefined) {
        const fromResult = parseResultNode(obj.result, visited);
        if (fromResult && fromResult.type !== "empty") return fromResult;
    }

    const fromFlat = dictToKvDataset(omitMetaEntries(obj));
    if (fromFlat) return fromFlat;

    return { type: "empty", message: JSON.stringify(obj, null, 2) };
}

/** POST /tool/exec result → 미리보기 표·수식 뷰 (meta 필드 제외) */
export function parseExecVisualResult(result: unknown): VisualResult {
    if (result === null || result === undefined) {
        return { type: "empty", message: "실행 결과가 없습니다." };
    }

    if (typeof result !== "object") {
        return { type: "empty", message: String(result) };
    }

    const parsed = parseExecVisualResultInner(result as Record<string, unknown>, new Set());
    const sourceFields = countSourceFields(result);
    const displayedFields = countDisplayedFields(parsed);

    const needsFallback =
        parsed.type === "empty"
        || (sourceFields > 0 && displayedFields < Math.max(1, Math.floor(sourceFields * 0.6)));

    if (needsFallback) {
        const fallback = genericFlattenFallback(result as Record<string, unknown>);
        if (fallback && countDisplayedFields(fallback) >= displayedFields) {
            return fallback;
        }
    }

    return parsed;
}
