import type { StateCreator } from "zustand";
import {
    INITIAL_TRACE_LOGS,
    UNSELECTED_TRACE_LOGS,
} from "./constants";
import { buildConsoleWaitingPreview } from "./consolePreview";
import type { VisualResult } from "./types";

export type ExecSliceState = {
    traceLogs: string[];
    jsonPreview: string;
    visualResult: VisualResult | null;
    execStatus: "idle" | "running" | "done" | "error";
    consoleStatus: "ready" | "running" | "success" | "error";
};

export type ExecSliceActions = {
    appendTraceLog: (line: string) => void;
    appendTraceLogs: (lines: string[]) => void;
    setTraceLogs: (lines: string[]) => void;
    setJsonPreview: (preview: string) => void;
    setVisualResult: (result: VisualResult | null) => void;
    setExecStatus: (status: ExecSliceState["execStatus"]) => void;
    setConsoleStatus: (status: ExecSliceState["consoleStatus"]) => void;
    clearExecState: () => void;
    resetExecPreview: (mode: "idle" | "selected" | "new", toolTitle?: string) => void;
};

export type ExecSlice = ExecSliceState & ExecSliceActions;

export const createExecSlice: StateCreator<ExecSlice, [], [], ExecSlice> = (set) => ({
    traceLogs: [...UNSELECTED_TRACE_LOGS],
    jsonPreview: buildConsoleWaitingPreview("idle"),
    visualResult: null,
    execStatus: "idle",
    consoleStatus: "ready",

    appendTraceLog: (line) =>
        set(state => ({ traceLogs: [...state.traceLogs, line] })),

    appendTraceLogs: (lines) =>
        set(state => ({ traceLogs: [...state.traceLogs, ...lines] })),

    setTraceLogs: (lines) => set({ traceLogs: lines }),

    setJsonPreview: (preview) => set({ jsonPreview: preview }),

    setVisualResult: (result) => set({ visualResult: result }),

    setExecStatus: (status) => set({ execStatus: status }),

    setConsoleStatus: (status) => set({ consoleStatus: status }),

    clearExecState: () =>
        set({
            traceLogs: [...UNSELECTED_TRACE_LOGS],
            jsonPreview: buildConsoleWaitingPreview("idle"),
            visualResult: null,
            execStatus: "idle",
            consoleStatus: "ready",
        }),

    resetExecPreview: (mode, toolTitle) => {
        if (mode === "selected" && toolTitle) {
            set({
                traceLogs: [...INITIAL_TRACE_LOGS],
                jsonPreview: buildConsoleWaitingPreview("selected"),
                visualResult: null,
                execStatus: "idle",
                consoleStatus: "ready",
            });
            return;
        }
        if (mode === "new") {
            set({
                traceLogs: [
                    ">_ // 대기 중: 도구 생성 진행 상황 로그가 실시간 노출됩니다.",
                ],
                jsonPreview: buildConsoleWaitingPreview("new"),
                visualResult: null,
                execStatus: "idle",
                consoleStatus: "ready",
            });
            return;
        }
        set({
            traceLogs: [...UNSELECTED_TRACE_LOGS],
            jsonPreview: buildConsoleWaitingPreview("idle"),
            visualResult: null,
            execStatus: "idle",
            consoleStatus: "ready",
        });
    },
});
