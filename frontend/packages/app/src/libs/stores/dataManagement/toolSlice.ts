import type { StateCreator } from "zustand";

export type ToolSliceState = {
    selectedToolId: string | null;
    toolPreviewResult: string | null;
    isPreviewLoading: boolean;
    execQuery: string;
    execQueryPlaceholder: string;
};

export type ToolSliceActions = {
    setSelectedToolId: (id: string | null) => void;
    setToolPreviewResult: (result: string | null) => void;
    setPreviewLoading: (v: boolean) => void;
    setExecQuery: (query: string) => void;
    setExecQueryPlaceholder: (placeholder: string) => void;
    clearTool: () => void;
};

export const createToolSlice: StateCreator<
    ToolSliceState & ToolSliceActions,
    [],
    [],
    ToolSliceState & ToolSliceActions
> = (set) => ({
    selectedToolId: null,
    toolPreviewResult: null,
    isPreviewLoading: false,
    execQuery: "",
    execQueryPlaceholder: "",

    setSelectedToolId: (id) => set({ selectedToolId: id }),
    setToolPreviewResult: (result) => set({ toolPreviewResult: result }),
    setPreviewLoading: (v) => set({ isPreviewLoading: v }),
    setExecQuery: (query) => set({ execQuery: query }),
    setExecQueryPlaceholder: (placeholder) => set({ execQueryPlaceholder: placeholder }),

    clearTool: () =>
        set({
            selectedToolId: null,
            toolPreviewResult: null,
            isPreviewLoading: false,
            execQuery: "",
            execQueryPlaceholder: "",
        }),
});
