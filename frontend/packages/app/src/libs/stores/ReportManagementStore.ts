import { create } from "zustand";
import { devtools } from "zustand/middleware";
import type { SageData } from "@/features/data";
import type {
    RecommendedToolItem,
    ReportGenerateResult,
    ReportLifecycle,
    ReportListItem,
} from "@/features/report-management";
import {
    applyProgressEvent,
    createEmptyProgressSnapshot,
    finalizeProgressSnapshot,
    hydrateProgressFromPlan,
    type ReportProgressSnapshot,
} from "@/features/report-management/progressSteps";
import type { SSEEventData } from "@/features/Utils";

export type ReportDraftForm = {
    /** 화면 전용 — API title 미지원 */
    reportTitle: string;
    description: string;
    query: string;
};

export type ReportManagementState = {
    lifecycle: ReportLifecycle;
    selectedReport: ReportListItem | null;
    selectedData: SageData | null;
    selectedToolIds: string[];
    draftForm: ReportDraftForm;
    reportResult: ReportGenerateResult | null;
    currentRid: string | null;
    streamLogs: string[];
    progressSnapshot: ReportProgressSnapshot;
    generateError: string | null;
    execError: string | null;
    isStreaming: boolean;
};

export type ReportManagementActions = {
    startNewReport: () => void;
    selectPublishedReport: (report: ReportListItem, model?: SageData | null) => void;
    setSelectedData: (data: SageData | null) => void;
    clearSelectedData: () => void;
    toggleTool: (tool: RecommendedToolItem) => void;
    removeTool: (toolId: string) => void;
    clearTools: () => void;
    setDraftField: <K extends keyof ReportDraftForm>(key: K, value: ReportDraftForm[K]) => void;
    setLifecycle: (lifecycle: ReportLifecycle) => void;
    setReportResult: (result: ReportGenerateResult | null) => void;
    setCurrentRid: (rid: string | null) => void;
    appendStreamLog: (log: string) => void;
    clearStreamLogs: () => void;
    resetProgress: () => void;
    applyStreamEvent: (event: SSEEventData) => void;
    setIsStreaming: (v: boolean) => void;
    setGenerateError: (msg: string | null) => void;
    setExecError: (msg: string | null) => void;
    onGenerateSuccess: (result: ReportGenerateResult) => void;
    onPublishSuccess: (report: ReportListItem) => void;
    onExecSuccess: (result: ReportGenerateResult) => void;
    reset: () => void;
};

const emptyDraft: ReportDraftForm = {
    reportTitle: "",
    description: "",
    query: "",
};

const initialState: ReportManagementState = {
    lifecycle: "drafting",
    selectedReport: null,
    selectedData: null,
    selectedToolIds: [],
    draftForm: { ...emptyDraft },
    reportResult: null,
    currentRid: null,
    streamLogs: [],
    progressSnapshot: createEmptyProgressSnapshot(),
    generateError: null,
    execError: null,
    isStreaming: false,
};

function clearModelLinkedDraft(
    draftForm: ReportDraftForm,
): Pick<ReportManagementState, "selectedToolIds" | "draftForm"> {
    return {
        selectedToolIds: [],
        draftForm: { ...draftForm, query: "" },
    };
}

/** API description — description 우선, 없으면 화면 보고서명 */
export function resolveGenerateDescription(form: ReportDraftForm): string {
    return form.description.trim() || form.reportTitle.trim();
}

export function canSubmitGenerateDraft(
    selectedDid: string | null | undefined,
    form: ReportDraftForm,
): boolean {
    return Boolean(selectedDid) && Boolean(form.query.trim()) && Boolean(resolveGenerateDescription(form));
}

export const useReportManagementStore = create<ReportManagementState & ReportManagementActions>()(
    devtools(
        (set, get) => ({
            ...initialState,

            startNewReport: () =>
                set({
                    ...initialState,
                    lifecycle: "drafting",
                }),

            selectPublishedReport: (report, model = null) =>
                set({
                    lifecycle: "viewing",
                    selectedReport: report,
                    selectedData: model,
                    selectedToolIds: report.tools ?? [],
                    draftForm: {
                        reportTitle: report.title ?? report.description,
                        description: report.description,
                        query: report.query ?? "",
                    },
                    reportResult: null,
                    currentRid: report.rid,
                    generateError: null,
                    execError: null,
                    streamLogs: [],
                    progressSnapshot: createEmptyProgressSnapshot(),
                    isStreaming: false,
                }),

            setSelectedData: (data) =>
                set(s => ({
                    selectedData: data,
                    ...clearModelLinkedDraft(s.draftForm),
                    generateError: null,
                })),

            clearSelectedData: () =>
                set(s => ({
                    selectedData: null,
                    ...clearModelLinkedDraft(s.draftForm),
                })),

            toggleTool: (tool) => {
                const ids = get().selectedToolIds;
                const exists = ids.includes(tool.tool_id);
                set({
                    selectedToolIds: exists
                        ? ids.filter(id => id !== tool.tool_id)
                        : [...ids, tool.tool_id],
                });
            },

            removeTool: (toolId) =>
                set({ selectedToolIds: get().selectedToolIds.filter(id => id !== toolId) }),

            clearTools: () => set({ selectedToolIds: [] }),

            setDraftField: (key, value) =>
                set(s => ({ draftForm: { ...s.draftForm, [key]: value } })),

            setLifecycle: (lifecycle) => set({ lifecycle }),

            setReportResult: (result) => set({ reportResult: result }),

            setCurrentRid: (rid) => set({ currentRid: rid }),

            appendStreamLog: (log) =>
                set(s => ({ streamLogs: [...s.streamLogs, log] })),

            clearStreamLogs: () => set({ streamLogs: [] }),

            resetProgress: () =>
                set({
                    streamLogs: [],
                    progressSnapshot: createEmptyProgressSnapshot(),
                }),

            applyStreamEvent: (event) =>
                set(s => {
                    let next = applyProgressEvent(s.progressSnapshot, event as Record<string, unknown>);
                    const planCandidate = event.plan
                        ?? (event.result && typeof event.result === "object"
                            ? (event.result as { plan?: unknown }).plan
                            : undefined);
                    if (planCandidate && typeof planCandidate === "object") {
                        next = hydrateProgressFromPlan(
                            next,
                            planCandidate as { tasks?: Array<{ task_id?: string; title?: string; type?: string }> },
                        );
                    }
                    return {
                        progressSnapshot: next,
                        streamLogs: next.logs,
                    };
                }),

            setIsStreaming: (v) => set({ isStreaming: v }),

            setGenerateError: (msg) => set({ generateError: msg }),

            setExecError: (msg) => set({ execError: msg }),

            onGenerateSuccess: (result) =>
                set(s => {
                    const finalized = finalizeProgressSnapshot(s.progressSnapshot, result.plan);
                    return {
                        lifecycle: "completed",
                        reportResult: result,
                        currentRid: result.rid ?? get().currentRid,
                        generateError: null,
                        isStreaming: false,
                        progressSnapshot: finalized,
                        streamLogs: finalized.logs,
                    };
                }),

            onPublishSuccess: (report) =>
                set({
                    lifecycle: "published",
                    selectedReport: report,
                    currentRid: report.rid,
                }),

            onExecSuccess: (result) =>
                set(s => {
                    const finalized = finalizeProgressSnapshot(s.progressSnapshot, result.plan);
                    return {
                        reportResult: result,
                        execError: null,
                        isStreaming: false,
                        progressSnapshot: finalized,
                        streamLogs: finalized.logs,
                    };
                }),

            reset: () => set({ ...initialState }),
        }),
        { name: "report-management-store" },
    ),
);
