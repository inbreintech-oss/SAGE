import type { StateCreator } from "zustand";

export type LayoutMode = "browse" | "detail";

export type LayoutState = {
    layoutMode: LayoutMode;
    leftPanelCollapsed: boolean;
    rightPanelVisible: boolean;
};

export type LayoutActions = {
    enterDetailMode: () => void;
    enterBrowseMode: () => void;
    setLeftPanelCollapsed: (collapsed: boolean) => void;
    toggleLeftPanel: (collapsed?: boolean) => void;
    setRightPanelVisible: (visible: boolean) => void;
    toggleRightPanel: (visible?: boolean) => void;
};

export const createLayoutSlice: StateCreator<
    LayoutState & LayoutActions,
    [],
    [],
    LayoutState & LayoutActions
> = (set, get) => ({
    layoutMode: "browse",
    leftPanelCollapsed: false,
    rightPanelVisible: false,

    enterDetailMode: () =>
        set({
            layoutMode: "detail",
            leftPanelCollapsed: true,
            rightPanelVisible: true,
        }),

    enterBrowseMode: () =>
        set({
            layoutMode: "browse",
            leftPanelCollapsed: false,
            rightPanelVisible: false,
        }),

    setLeftPanelCollapsed: (collapsed) => set({ leftPanelCollapsed: collapsed }),

    toggleLeftPanel: (collapsed) => {
        const next = collapsed ?? !get().leftPanelCollapsed;
        if (!next) {
            // 좌측 목록 펼침 → 우측 스키마 패널 자동 접힘
            set({ leftPanelCollapsed: false, rightPanelVisible: false });
            return;
        }
        set({ leftPanelCollapsed: true });
    },

    setRightPanelVisible: (visible) => set({ rightPanelVisible: visible }),

    toggleRightPanel: (visible) => {
        const next = visible ?? !get().rightPanelVisible;
        set({ rightPanelVisible: next });
    },
});
