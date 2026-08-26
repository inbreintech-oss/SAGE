import type { StateCreator } from "zustand";
import type { ToolAssetStatus, ToolLifecycleStage } from "./types";

export type LifecycleSliceState = {
    lifecycleStage: ToolLifecycleStage;
    pendingToolId: string | null;
    callerScript: string | null;
    assetPath: string | null;
    isListAssetized: boolean;
};

export type LifecycleSliceActions = {
    resetLifecycle: () => void;
    markGenerated: (toolId: string, code: string, caller?: string) => void;
    markAssetized: (assetPath: string) => void;
    hydrateListTool: (toolId: string, status: ToolAssetStatus, caller?: string) => void;
};

export type LifecycleSlice = LifecycleSliceState & LifecycleSliceActions;

const initialLifecycle: LifecycleSliceState = {
    lifecycleStage: "draft",
    pendingToolId: null,
    callerScript: null,
    assetPath: null,
    isListAssetized: false,
};

export const createLifecycleSlice: StateCreator<
    LifecycleSlice & {
        patchFormField: (partial: { code?: string }) => void;
        setSelectedToolId: (id: string | null) => void;
    },
    [],
    [],
    LifecycleSlice
> = (set, get) => ({
    ...initialLifecycle,

    resetLifecycle: () => set({ ...initialLifecycle }),

    markGenerated: (toolId, code, caller) => {
        get().patchFormField({ code });
        get().setSelectedToolId(toolId);
        set({
            lifecycleStage: "generated",
            pendingToolId: toolId,
            callerScript: caller ?? null,
            isListAssetized: false,
        });
    },

    markAssetized: (assetPath) =>
        set({
            lifecycleStage: "assetized",
            assetPath,
            isListAssetized: true,
        }),

    hydrateListTool: (toolId, status, caller) =>
        set({
            lifecycleStage: status,
            pendingToolId: toolId,
            callerScript: caller ?? null,
            assetPath: null,
            isListAssetized: status === "assetized",
        }),
});

export function canExecTool(state: {
    lifecycleStage: ToolLifecycleStage;
    pendingToolId: string | null;
    selectedToolId: string | null;
}): boolean {
    const toolId = state.pendingToolId ?? state.selectedToolId;
    if (!toolId) return false;
    return state.lifecycleStage === "generated" || state.lifecycleStage === "assetized";
}
