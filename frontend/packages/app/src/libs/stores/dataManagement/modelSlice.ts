import type { StateCreator } from "zustand";
import type { SageData } from "@/features/data";
import { resolveSchemaFromSageData } from "@/features/data-management";
import type { PangeazeSchemaObject } from "@/features/data-analysis";
import { resolveCategoryCode } from "@/libs/stores/toolManagement/commonCodes";
import { DEFAULT_DATA_CATEGORY, DATA_SOURCE_DB_TAB_ENABLED, type DataCategoryValue } from "./constants";
import { MAX_ANALYSIS_FIELD_LENGTH, type TabType } from "./types";

export type ConsolePhase = "idle" | "streaming" | "completed";

export type ModelState = {
    selectedData: SageData | null;
    searchQuery: string;
    activeTab: TabType;
    analysisName: string;
    analysisDesc: string;
    analysisCategory: DataCategoryValue;
    errorMsg: string | null;
    saveStatus: "idle" | "saving" | "success" | "error";
    schemaResult: PangeazeSchemaObject | null;
    saveDatasetsJson: string | null;
    /** Pangeaze / List Data 의 suggested_queries */
    suggestedQueries: string[];
    streamLogs: string[];
    isBuilding: boolean;
    consolePhase: ConsolePhase;
};

export type ModelActions = {
    setSelectedData: (data: SageData | null) => void;
    setSearchQuery: (q: string) => void;
    setActiveTab: (tab: TabType) => void;
    setAnalysisName: (name: string, existingNames: string[]) => void;
    setAnalysisDesc: (desc: string) => void;
    setAnalysisCategory: (category: DataCategoryValue) => void;
    setErrorMsg: (msg: string | null) => void;
    setSaveStatus: (status: ModelState["saveStatus"]) => void;
    setSchemaResult: (schema: PangeazeSchemaObject | null) => void;
    setSaveDatasetsJson: (json: string | null) => void;
    setSuggestedQueries: (queries: string[]) => void;
    appendStreamLog: (log: string) => void;
    clearStreamLogs: () => void;
    setIsBuilding: (v: boolean) => void;
    setConsolePhase: (phase: ConsolePhase) => void;
    loadModel: (item: SageData) => void;
};

function clampField(value: string): string {
    return value.slice(0, MAX_ANALYSIS_FIELD_LENGTH);
}

export const createModelSlice: StateCreator<
    ModelState & ModelActions,
    [],
    [],
    ModelState & ModelActions
> = (set) => ({
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

    setSelectedData: (data) => set({ selectedData: data }),
    setSearchQuery: (q) => set({ searchQuery: q }),
    setActiveTab: (tab) =>
        set({
            activeTab: tab === "db" && !DATA_SOURCE_DB_TAB_ENABLED ? "xlsx" : tab,
        }),

    setAnalysisName: (name, _existingNames) =>
        set({ analysisName: clampField(name) }),

    setAnalysisDesc: (desc) =>
        set({ analysisDesc: clampField(desc) }),

    setAnalysisCategory: (category) => set({ analysisCategory: category }),

    setErrorMsg: (msg) => set({ errorMsg: msg }),
    setSaveStatus: (status) => set({ saveStatus: status }),
    setSchemaResult: (schema) => set({ schemaResult: schema }),
    setSaveDatasetsJson: (json) => set({ saveDatasetsJson: json }),
    setSuggestedQueries: (queries) => set({ suggestedQueries: queries }),
    appendStreamLog: (log) => set(s => ({ streamLogs: [...s.streamLogs, log] })),
    clearStreamLogs: () => set({ streamLogs: [] }),
    setIsBuilding: (v) => set({ isBuilding: v }),
    setConsolePhase: (phase) => set({ consolePhase: phase }),

    loadModel: (item) =>
        set({
            selectedData: item,
            analysisName: item.name,
            analysisDesc: item.description ?? "",
            analysisCategory: resolveCategoryCode(item.category),
            streamLogs: [],
            schemaResult: resolveSchemaFromSageData(item),
            saveDatasetsJson: null,
            suggestedQueries: item.suggested_queries ?? [],
            errorMsg: null,
            saveStatus: "idle",
            consolePhase: "idle",
        }),
});

export const selectIsNewMode = (s: ModelState): boolean => s.selectedData === null;
