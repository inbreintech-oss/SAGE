import type { StateCreator } from "zustand";

export type UiSliceState = {
    leftPanelCollapsed: boolean;
};

export type UiSliceActions = {
    setLeftPanelCollapsed: (collapsed: boolean) => void;
    toggleLeftPanel: (collapse: boolean) => void;
};

export type UiSlice = UiSliceState & UiSliceActions;

export const createUiSlice: StateCreator<UiSlice, [], [], UiSlice> = (set) => ({
    leftPanelCollapsed: false,

    setLeftPanelCollapsed: (collapsed) => set({ leftPanelCollapsed: collapsed }),

    toggleLeftPanel: (collapse) => set({ leftPanelCollapsed: collapse }),
});
