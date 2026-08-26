import type { UploadedFile } from "@/features/data-analysis";
import { CSV_DEFAULT_SHEET_NAME, isCsvFormat } from "@/features/data/sourceSchema";

export type TabType = "xlsx" | "api" | "db";

export type DbVendor = "postgresql" | "mssql";

export type DbColumnMeta = {
    name: string;
    type: string;
    selected: boolean;
};

export type DbForm = {
    vendor: DbVendor;
    host: string;
    port: string;
    dbName: string;
    tableName: string;
    username: string;
    password: string;
    query: string;
};

export type DbPoolSeal = DbForm & {
    columns: DbColumnMeta[];
};

export const DB_VENDOR_DEFAULT_PORTS: Record<DbVendor, string> = {
    postgresql: "5432",
    mssql: "1433",
};

export const EMPTY_DB_FORM: DbForm = {
    vendor: "postgresql",
    host: "",
    port: DB_VENDOR_DEFAULT_PORTS.postgresql,
    dbName: "",
    tableName: "",
    username: "",
    password: "",
    query: "",
};

export const MAX_ANALYSIS_FIELD_LENGTH = 256;

/** 개별 Column — Sheet에 종속, 고유 id 독립 관리 */
export type DmColumn = {
    id: string;
    name: string;
    dtype: string;
    selected: boolean;
};

/** 개별 Sheet — File에 종속 */
export type DmSheet = {
    id: string;
    name: string;
    columns: DmColumn[];
};

/** 업로드된 File 루트 노드 */
export type DmFileNode = {
    id: string;
    filename: string;
    path: string;
    fileType: string;
    sheets: DmSheet[];
    activeSheetId: string | null;
};

export type PoolFileItem = {
    poolId: string;
    type: "file";
    displayName: string;
    sealed: {
        fileId: string;
        hierarchy: DmFileNode;
    };
};

export type PoolToolItem = {
    poolId: string;
    type: "tool";
    displayName: string;
    sealed: {
        toolId: string;
    };
};

export type PoolDbItem = {
    poolId: string;
    type: "db";
    displayName: string;
    sealed: DbPoolSeal;
};

export type PoolItem = PoolFileItem | PoolToolItem | PoolDbItem;

function newId(): string {
    return crypto.randomUUID();
}

/** UploadedFile API 응답 → DmFileNode 정규화 */
export function normalizeUploadedFile(raw: UploadedFile): DmFileNode {
    const fileId = newId();
    const isCsv = isCsvFormat(raw.file_type, raw.path ?? raw.filename);

    if (isCsv) {
        const firstMeta = raw.metadata[0];
        const sheetId = newId();
        const sheet: DmSheet = {
            id: sheetId,
            name: CSV_DEFAULT_SHEET_NAME,
            columns: (firstMeta?.columns ?? []).map(col => ({
                id: newId(),
                name: col.name,
                dtype: col.dtype,
                selected: true,
            })),
        };

        return {
            id: fileId,
            filename: raw.filename,
            path: raw.path,
            fileType: raw.file_type,
            sheets: [sheet],
            activeSheetId: sheetId,
        };
    }

    const sheets: DmSheet[] = raw.metadata.map(meta => {
        const sheetId = newId();
        return {
            id: sheetId,
            name: meta.name,
            columns: meta.columns.map(col => ({
                id: newId(),
                name: col.name,
                dtype: col.dtype,
                selected: true,
            })),
        };
    });

    return {
        id: fileId,
        filename: raw.filename,
        path: raw.path,
        fileType: raw.file_type,
        sheets,
        activeSheetId: sheets[0]?.id ?? null,
    };
}

export function cloneFileNode(node: DmFileNode): DmFileNode {
    return structuredClone(node);
}
