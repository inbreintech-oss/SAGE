import type { DmColumn, DmFileNode, DmSheet, PoolItem } from "./types";

/** Pool 비교용 정규화 스냅샷 (키 정렬 + 선택 상태만 추출) */
export type NormalizedPoolSnapshot = {
    items: NormalizedPoolEntry[];
};

type NormalizedPoolEntry =
    | {
          type: "file";
          displayName: string;
          fileId: string;
          path: string;
          sheets: NormalizedSheet[];
      }
    | {
          type: "tool";
          displayName: string;
          toolId: string;
      }
    | {
          type: "db";
          displayName: string;
          host: string;
          port: string;
          dbName: string;
          tableName: string;
          query: string;
          sheets: { name: string; columns: { name: string; type: string; selected: boolean }[] }[];
      };

type NormalizedSheet = {
    sheetId: string;
    name: string;
    columns: { columnId: string; name: string; dtype: string; selected: boolean }[];
};

function normalizeFileHierarchy(file: DmFileNode): NormalizedSheet[] {
    return [...file.sheets]
        .sort((a, b) => a.id.localeCompare(b.id))
        .map((sheet: DmSheet) => ({
            sheetId: sheet.id,
            name: sheet.name,
            columns: [...sheet.columns]
                .sort((a, b) => a.id.localeCompare(b.id))
                .map((col: DmColumn) => ({
                    columnId: col.id,
                    name: col.name,
                    dtype: col.dtype,
                    selected: col.selected,
                })),
        }));
}

export function normalizePoolItems(items: PoolItem[]): NormalizedPoolSnapshot {
    const normalized = items.map((item): NormalizedPoolEntry => {
        if (item.type === "file") {
            const { hierarchy } = item.sealed;
            return {
                type: "file",
                displayName: item.displayName,
                fileId: item.sealed.fileId,
                path: hierarchy.path,
                sheets: normalizeFileHierarchy(hierarchy),
            };
        }
        if (item.type === "tool") {
            return {
                type: "tool",
                displayName: item.displayName,
                toolId: item.sealed.toolId,
            };
        }
        return {
            type: "db",
            displayName: item.displayName,
            host: item.sealed.host,
            port: item.sealed.port,
            dbName: item.sealed.dbName,
            tableName: item.sealed.tableName,
            query: item.sealed.query,
            sheets: [{
                name: item.sealed.tableName,
                columns: [...item.sealed.columns]
                    .sort((a, b) => a.name.localeCompare(b.name))
                    .map(col => ({
                        name: col.name,
                        type: col.type,
                        selected: col.selected,
                    })),
            }],
        };
    });

    normalized.sort((a, b) => {
        const keyA = `${a.type}::${a.displayName}`;
        const keyB = `${b.type}::${b.displayName}`;
        return keyA.localeCompare(keyB);
    });

    return { items: normalized };
}

function deepEqual(a: unknown, b: unknown): boolean {
    if (a === b) return true;
    if (a === null || b === null || typeof a !== typeof b) return false;

    if (Array.isArray(a) && Array.isArray(b)) {
        if (a.length !== b.length) return false;
        return a.every((val, i) => deepEqual(val, b[i]));
    }

    if (typeof a === "object" && typeof b === "object") {
        const keysA = Object.keys(a as object).sort();
        const keysB = Object.keys(b as object).sort();
        if (keysA.length !== keysB.length) return false;
        return keysA.every((key, i) => key === keysB[i]
            && deepEqual(
                (a as Record<string, unknown>)[key],
                (b as Record<string, unknown>)[key],
            ));
    }

    return false;
}

export function poolsAreEqual(current: PoolItem[], baseline: PoolItem[]): boolean {
    return deepEqual(
        normalizePoolItems(current),
        normalizePoolItems(baseline),
    );
}

export function fingerprintPool(items: PoolItem[]): string {
    return JSON.stringify(normalizePoolItems(items));
}
