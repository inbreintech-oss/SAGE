import type { StateCreator } from "zustand";
import type { DataSource } from "@/features/data";
import {
    buildDbSourcePath,
    fileSourceOptions,
    isCsvFormat,
    mapDmColumnsToApiColumns,
    normalizeImportedSheetName,
    resolveApiSheetName,
    resolveSourceSheets,
    type DataSourceSheet,
} from "@/features/data/sourceSchema";
import { buildFilePoolId } from "./poolUtils";
import type { DbPoolSeal, DmFileNode, PoolItem } from "./types";
import { cloneFileNode } from "./types";

export type PoolState = {
    poolItems: PoolItem[];
    baselinePoolItems: PoolItem[];
    activePoolId: string | null;
};

export type PoolActions = {
    addFileToPool: (file: DmFileNode) => string | false;
    addToolToPool: (toolId: string, displayName: string) => string | false;
    addDbToPool: (seal: DbPoolSeal, displayName: string) => string | false;
    removeFromPool: (poolId: string) => void;
    selectPoolItem: (poolId: string | null) => void;
    clearActivePoolItem: () => void;
    setPoolFromModel: (items: PoolItem[]) => void;
    refreshPoolToolDisplayNames: (toolTitleById: Record<string, string>) => void;
    clearPool: () => void;
    updateFileInPool: (poolId: string, hierarchy: DmFileNode) => void;
};

/** 파일 system path → 파일명 (도구명·모델명 등 표시 라벨에는 사용하지 않음) */
function extractPathBasename(path: string): string {
    return path.split("/").pop() ?? path;
}

function trimDisplayLabel(label: string): string {
    return label.trim();
}

/** path·URL 형태 tool 참조 → canonical tool_id */
export function normalizeToolId(pathOrId: string): string {
    const trimmed = pathOrId.trim();
    if (!trimmed) return trimmed;
    const segments = trimmed.split(/[/\\]/).filter(Boolean);
    return segments[segments.length - 1] ?? trimmed;
}

export function isToolDataSource(src: Pick<DataSource, "type">): boolean {
    return src.type?.toLowerCase() === "tool";
}

export function resolveToolSourceId(src: Pick<DataSource, "path" | "id">): string {
    return normalizeToolId(src.path || src.id || "");
}

/** API origin 또는 도구 목록 lookup 으로 Pool tool displayName 결정 */
export function resolveToolDisplayName(
    toolId: string,
    origin: string | undefined,
    toolTitleById?: Record<string, string>,
): string {
    const normalizedId = normalizeToolId(toolId);
    const fromCatalog =
        toolTitleById?.[normalizedId]?.trim()
        ?? toolTitleById?.[toolId]?.trim();
    if (fromCatalog) return fromCatalog;

    const fromOrigin = origin?.trim();
    if (fromOrigin && fromOrigin !== normalizedId) {
        return fromOrigin;
    }
    return normalizedId || toolId;
}

function applyToolDisplayNameLookup(
    items: PoolItem[],
    toolTitleById: Record<string, string>,
): PoolItem[] {
    return items.map(item => {
        if (item.type !== "tool") return item;
        const normalizedId = normalizeToolId(item.sealed.toolId);
        const originHint = item.displayName === item.sealed.toolId || item.displayName === normalizedId
            ? undefined
            : item.displayName;
        const resolved = resolveToolDisplayName(
            item.sealed.toolId,
            originHint,
            toolTitleById,
        );
        if (resolved === item.displayName && normalizedId === item.sealed.toolId) return item;
        return {
            ...item,
            poolId: `tool::${normalizedId}`,
            displayName: resolved,
            sealed: { toolId: normalizedId },
        };
    });
}

export const createPoolSlice: StateCreator<
    PoolState & PoolActions,
    [],
    [],
    PoolState & PoolActions
> = (set, get) => ({
    poolItems: [],
    baselinePoolItems: [],
    activePoolId: null,

    addFileToPool: (file) => {
        const poolId = buildFilePoolId(file.id, file.activeSheetId);
        if (get().poolItems.some(p => p.poolId === poolId)) return false;

        set(s => ({
            poolItems: [
                ...s.poolItems,
                {
                    poolId,
                    type: "file",
                    displayName: file.filename,
                    sealed: { fileId: file.id, hierarchy: cloneFileNode(file) },
                },
            ],
            activePoolId: poolId,
        }));
        return poolId;
    },

    addToolToPool: (toolId, displayName) => {
        const normalizedId = normalizeToolId(toolId);
        const poolId = `tool::${normalizedId}`;
        if (get().poolItems.some(p => p.poolId === poolId)) return false;

        set(s => ({
            poolItems: [
                ...s.poolItems,
                {
                    poolId,
                    type: "tool",
                    displayName: trimDisplayLabel(displayName),
                    sealed: { toolId: normalizedId },
                },
            ],
            activePoolId: poolId,
        }));
        return poolId;
    },

    addDbToPool: (seal, displayName) => {
        const poolId = `db::${seal.vendor}::${seal.host}::${seal.dbName}::${seal.tableName}`;
        if (get().poolItems.some(p => p.poolId === poolId)) return false;

        set(s => ({
            poolItems: [
                ...s.poolItems,
                {
                    poolId,
                    type: "db",
                    displayName,
                    sealed: {
                        ...seal,
                        columns: seal.columns.map(c => ({ ...c })),
                    },
                },
            ],
            activePoolId: poolId,
        }));
        return poolId;
    },

    removeFromPool: (poolId) =>
        set(s => ({
            poolItems: s.poolItems.filter(p => p.poolId !== poolId),
            activePoolId: s.activePoolId === poolId ? null : s.activePoolId,
        })),

    selectPoolItem: (poolId) =>
        set({ activePoolId: poolId }),

    clearActivePoolItem: () =>
        set({ activePoolId: null }),

    setPoolFromModel: (items) =>
        set({
            poolItems: items.map(item => structuredClone(item)),
            baselinePoolItems: items.map(item => structuredClone(item)),
            activePoolId: null,
        }),

    refreshPoolToolDisplayNames: (toolTitleById) =>
        set(s => ({
            poolItems: applyToolDisplayNameLookup(s.poolItems, toolTitleById),
            baselinePoolItems: applyToolDisplayNameLookup(s.baselinePoolItems, toolTitleById),
        })),

    clearPool: () =>
        set({ poolItems: [], baselinePoolItems: [], activePoolId: null }),

    updateFileInPool: (poolId, hierarchy) =>
        set(s => ({
            poolItems: s.poolItems.map(p =>
                p.poolId === poolId && p.type === "file"
                    ? { ...p, sealed: { ...p.sealed, hierarchy: cloneFileNode(hierarchy) } }
                    : p
            ),
        })),
});

/** SageData.sources → PoolItem[] 역파싱 (기등록 모델 로드, API v1.1 sheets) */
export function poolItemsFromSources(
    sources: DataSource[] = [],
    toolTitleById?: Record<string, string>,
): PoolItem[] {
    const items: PoolItem[] = [];

    for (const src of sources) {
        if (src.type === "file") {
            const filename = extractPathBasename(src.path);
            const fileId = src.id ?? crypto.randomUUID();
            const format = src.format ?? "xlsx";
            const isCsv = isCsvFormat(format, src.path);
            const apiSheets = resolveSourceSheets(src).map(sheet => ({
                ...sheet,
                name: normalizeImportedSheetName(format, sheet.name, src.path),
            }));

            const sheetsToImport = isCsv
                ? apiSheets.slice(0, 1)
                : apiSheets;

            for (const apiSheet of sheetsToImport) {
                const sheetId = crypto.randomUUID();
                const hierarchy: DmFileNode = {
                    id: fileId,
                    filename,
                    path: src.path,
                    fileType: format,
                    activeSheetId: sheetId,
                    sheets: [{
                        id: sheetId,
                        name: apiSheet.name,
                        columns: apiSheet.columns.map(col => ({
                            id: crypto.randomUUID(),
                            name: col.name,
                            dtype: col.type,
                            selected: col.selected,
                        })),
                    }],
                };

                items.push({
                    poolId: buildFilePoolId(fileId, sheetId),
                    type: "file",
                    displayName: filename,
                    sealed: { fileId, hierarchy },
                });
            }
        } else if (isToolDataSource(src)) {
            const toolId = resolveToolSourceId(src);
            if (!toolId) continue;
            items.push({
                poolId: `tool::${toolId}`,
                type: "tool",
                displayName: resolveToolDisplayName(toolId, src.origin, toolTitleById),
                sealed: { toolId },
            });
        } else if (src.type === "db") {
            const opts = src.options ?? {};
            const apiSheets = resolveSourceSheets(src);
            const primarySheet = apiSheets[0];
            const tableName = primarySheet?.name
                ?? opts.tableName as string | undefined
                ?? src.path.split("/").pop()
                ?? "table";
            const columns = primarySheet?.columns.map(col => ({
                name: col.name,
                type: col.type,
                selected: col.selected,
            })) ?? [];

            items.push({
                poolId: `db::${opts.vendor ?? "postgresql"}::${opts.host ?? ""}::${opts.dbName ?? ""}::${tableName}`,
                type: "db",
                displayName: `${tableName} @ ${opts.host ?? ""}`,
                sealed: {
                    vendor: (opts.vendor as DbPoolSeal["vendor"]) ?? "postgresql",
                    host: String(opts.host ?? ""),
                    port: String(opts.port ?? ""),
                    dbName: String(opts.dbName ?? ""),
                    tableName,
                    username: String(opts.username ?? ""),
                    password: "",
                    query: String(opts.query ?? ""),
                    columns,
                },
            });
        }
    }

    return items;
}

function resolveActiveSheet(hierarchy: DmFileNode) {
    return hierarchy.sheets.find(s => s.id === hierarchy.activeSheetId)
        ?? hierarchy.sheets[0]
        ?? null;
}

/** 동일 path의 Pool file 항목 → sheets[] 병합 (서버: source 1개 / file) */
function mergeFilePoolSheets(group: PoolItem[]): DataSourceSheet[] {
    const sheets: DataSourceSheet[] = [];
    const seenNames = new Set<string>();

    for (const item of group) {
        if (item.type !== "file") continue;
        const { hierarchy } = item.sealed;
        const activeSheet = resolveActiveSheet(hierarchy);
        if (!activeSheet) continue;

        const apiName = resolveApiSheetName(hierarchy.fileType, activeSheet.name, hierarchy.path);
        if (seenNames.has(apiName)) continue;
        seenNames.add(apiName);

        sheets.push({
            name: apiName,
            columns: mapDmColumnsToApiColumns(activeSheet.columns),
        });
    }

    return sheets;
}

/**
 * Pool → API sources[] 변환.
 * 서버 스펙: sources[]에 file·tool·db 각각 N개 가능.
 * - file: path당 1 source, 동일 파일·다중 시트는 sheets[]로 병합
 * - tool: tool_id(path)당 1 source
 * - db: 연결 path(host/dbName/tableName)당 1 source
 */
export function poolItemsToDataSources(items: PoolItem[]): DataSource[] {
    const sources: DataSource[] = [];
    const emittedFiles = new Set<string>();
    const emittedTools = new Set<string>();
    const emittedDbs = new Set<string>();

    const fileGroups = new Map<string, PoolItem[]>();
    for (const item of items) {
        if (item.type !== "file") continue;
        const path = item.sealed.hierarchy.path;
        const group = fileGroups.get(path) ?? [];
        group.push(item);
        fileGroups.set(path, group);
    }

    const dbGroups = new Map<string, PoolItem[]>();
    for (const item of items) {
        if (item.type !== "db") continue;
        const path = buildDbSourcePath(item.sealed.host, item.sealed.dbName, item.sealed.tableName);
        const group = dbGroups.get(path) ?? [];
        group.push(item);
        dbGroups.set(path, group);
    }

    for (const item of items) {
        if (item.type === "file") {
            const path = item.sealed.hierarchy.path;
            if (emittedFiles.has(path)) continue;
            emittedFiles.add(path);

            const group = fileGroups.get(path) ?? [];
            const ref = group.find(p => p.type === "file");
            if (!ref || ref.type !== "file") continue;
            const { hierarchy } = ref.sealed;

            sources.push({
                type: "file",
                path,
                format: hierarchy.fileType,
                options: fileSourceOptions(hierarchy.fileType),
                sheets: mergeFilePoolSheets(group),
            });
        } else if (item.type === "tool") {
            const path = normalizeToolId(item.sealed.toolId);
            if (emittedTools.has(path)) continue;
            emittedTools.add(path);
            sources.push({
                type: "tool",
                path,
                ...(item.displayName.trim()
                    ? { origin: item.displayName.trim() }
                    : {}),
            });
        } else if (item.type === "db") {
            const seal = item.sealed;
            const path = buildDbSourcePath(seal.host, seal.dbName, seal.tableName);
            if (emittedDbs.has(path)) continue;
            emittedDbs.add(path);

            const group = dbGroups.get(path) ?? [item];
            const ref = group.find(p => p.type === "db");
            if (!ref || ref.type !== "db") continue;

            sources.push({
                type: "db",
                path,
                options: {
                    vendor: ref.sealed.vendor,
                    host: ref.sealed.host,
                    port: ref.sealed.port,
                    dbName: ref.sealed.dbName,
                    tableName: ref.sealed.tableName,
                    username: ref.sealed.username,
                    query: ref.sealed.query,
                },
                sheets: [{
                    name: ref.sealed.tableName,
                    columns: ref.sealed.columns.map(col => ({
                        name: col.name,
                        type: col.type,
                        selected: col.selected,
                    })),
                }],
            });
        }
    }

    return sources;
}
