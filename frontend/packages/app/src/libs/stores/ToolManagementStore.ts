import { create } from "zustand";
import { devtools } from "zustand/middleware";
import {
    createDirtyGuardSlice,
    type DirtyGuardSlice,
} from "./toolManagement/dirtyGuardSlice";
import { createExecSlice, type ExecSlice } from "./toolManagement/execSlice";
import { createFormSlice, type FormSlice } from "./toolManagement/formSlice";
import { createLifecycleSlice, type LifecycleSlice } from "./toolManagement/lifecycleSlice";
import { createSearchSlice, type SearchSlice } from "./toolManagement/searchSlice";
import { createUiSlice, type UiSlice } from "./toolManagement/uiSlice";
import type { ToolListItem } from "./toolManagement/types";

type ListSlice = {
    tools: ToolListItem[];
    listStatus: "idle" | "loading" | "success" | "error";
    listError: string | null;
    setTools: (tools: ToolListItem[]) => void;
    setListStatus: (status: ListSlice["listStatus"]) => void;
    setListError: (error: string | null) => void;
    resetAll: () => void;
};

export type ToolManagementStore =
    & ListSlice
    & FormSlice
    & SearchSlice
    & DirtyGuardSlice
    & LifecycleSlice
    & ExecSlice
    & UiSlice;

export const useToolManagementStore = create<ToolManagementStore>()(
    devtools(
        (set, get, api) => ({
            tools: [],
            listStatus: "idle",
            listError: null,

            setTools: (tools) => set({ tools }),
            setListStatus: (listStatus) => set({ listStatus }),
            setListError: (listError) => set({ listError }),

            ...createSearchSlice(set, get, api),
            ...createFormSlice(set, get, api),
            ...createLifecycleSlice(set, get, api),
            ...createDirtyGuardSlice(set, get, api),
            ...createExecSlice(set, get, api),
            ...createUiSlice(set, get, api),

            resetAll: () => {
                get().clearSelection();
                get().clearSearch();
                get().clearExecState();
                get().toggleLeftPanel(false);
                set({ tools: [], listStatus: "idle", listError: null });
            },
        }),
        { name: "ToolManagementStore" },
    ),
);
