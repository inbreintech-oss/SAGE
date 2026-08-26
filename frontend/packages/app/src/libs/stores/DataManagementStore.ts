import { create } from "zustand";
import { devtools } from "zustand/middleware";
import type { SageData } from "@/features/data";
import {
    createDirtyGuardSlice,
    type DirtyGuardActions,
    type DirtyGuardState,
} from "./dataManagement/dirtyGuardSlice";
import {
    createDbSlice,
    type DbSliceActions,
    type DbSliceState,
} from "./dataManagement/dbSlice";
import {
    createFileHierarchySlice,
    type FileHierarchyActions,
    type FileHierarchyState,
} from "./dataManagement/fileHierarchySlice";
import {
    createModelSlice,
    type ModelActions,
    type ModelState,
} from "./dataManagement/modelSlice";
import {
    createPoolSlice,
    poolItemsFromSources,
    type PoolActions,
    type PoolState,
} from "./dataManagement/poolSlice";
import {
    createToolSlice,
    type ToolSliceActions,
    type ToolSliceState,
} from "./dataManagement/toolSlice";
import {
    createLayoutSlice,
    type LayoutActions,
    type LayoutState,
} from "./dataManagement/layoutSlice";
import { resolveHasActiveSchema } from "./dataManagement/schemaResolver";
import { DEFAULT_DATA_CATEGORY, DATA_SOURCE_DB_TAB_ENABLED } from "./dataManagement/constants";
import type { DbPoolSeal } from "./dataManagement/types";
import { resolveSourceSheets } from "@/features/data/sourceSchema";

export type DataManagementStore =
    & ModelState & ModelActions
    & LayoutState & LayoutActions
    & FileHierarchyState & FileHierarchyActions
    & PoolState & PoolActions
    & DirtyGuardState & DirtyGuardActions
    & ToolSliceState & ToolSliceActions
    & DbSliceState & DbSliceActions
    & {
        resetAll: () => void;
        startNewAnalysis: () => void;
        hydrateFromModel: (
            item: SageData,
            options?: { toolTitleById?: Record<string, string> },
        ) => void;
    };

const initialModel: ModelState = {
    selectedData: null,
    searchQuery: "",
    activeTab: "xlsx",
    analysisName: "",
    analysisDesc: "",
    analysisCategory: DEFAULT_DATA_CATEGORY,
    errorMsg: null,
    saveStatus: "idle",
    schemaResult: null,
    saveDatasetsJson: null,
    suggestedQueries: [],
    streamLogs: [],
    isBuilding: false,
    consolePhase: "idle",
};

export const useDataManagementStore = create<DataManagementStore>()(
    devtools(
        (set, get, api) => ({
            ...createModelSlice(set, get, api),
            ...createLayoutSlice(set, get, api),
            ...createFileHierarchySlice(set, get, api),
            ...createPoolSlice(set, get, api),
            ...createDirtyGuardSlice(set, get, api),
            ...createToolSlice(set, get, api),
            ...createDbSlice(set, get, api),

            resetAll: () => {
                get().clearFile();
                get().clearPool();
                get().clearTool();
                get().clearDb();
                get().resetDirtyGuard();
                set({
                    ...initialModel,
                    activeTab: "xlsx",
                });
            },

            /** 신규 분석 — 폼 초기화 + Detail 레이아웃(우측 패널 펼침) 원자 적용 */
            startNewAnalysis: () => {
                get().clearFile();
                get().clearPool();
                get().clearTool();
                get().clearDb();
                get().resetDirtyGuard();
                set({
                    ...initialModel,
                    activeTab: "xlsx",
                    layoutMode: "detail",
                    leftPanelCollapsed: true,
                    rightPanelVisible: true,
                });
            },

            hydrateFromModel: (item, options) => {
                get().loadModel(item);
                const pool = poolItemsFromSources(item.sources, options?.toolTitleById);
                get().setPoolFromModel(pool);
                get().captureBaseline(item.did, item.name);
                get().setHasActiveSchema(resolveHasActiveSchema(item));
                get().clearFile();
                get().clearTool();

                const dbSource = item.sources?.find(s => s.type === "db");
                if (dbSource) {
                    const opts = dbSource.options ?? {};
                    const apiSheets = resolveSourceSheets(dbSource);
                    const primarySheet = apiSheets[0];
                    const tableName = primarySheet?.name
                        || (opts.tableName ? String(opts.tableName) : "")
                        || dbSource.path.split("/").pop()
                        || "table";
                    get().lockDbForm({
                        vendor: (opts.vendor as DbPoolSeal["vendor"]) ?? "postgresql",
                        host: String(opts.host ?? ""),
                        port: String(opts.port ?? ""),
                        dbName: String(opts.dbName ?? ""),
                        tableName,
                        username: String(opts.username ?? ""),
                        password: "",
                        query: String(opts.query ?? ""),
                        columns: primarySheet?.columns.map(col => ({
                            name: col.name,
                            type: col.type,
                            selected: col.selected,
                        })) ?? [],
                    });
                    set({
                        activeTab: DATA_SOURCE_DB_TAB_ENABLED ? "db" : "xlsx",
                    });
                } else {
                    get().unlockDbForm();
                    get().clearDb();
                }
            },
        }),
        { name: "data-management-store" },
    ),
);
