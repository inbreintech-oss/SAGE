import type { StateCreator } from "zustand";
import { DEFAULT_NEW_TOOL_CODE, DEFAULT_CATEGORY_CODE } from "./constants";
import type { ToolAssetStatus, ToolEditorMode, ToolFormDraft, ToolListItem } from "./types";

export const emptyFormDraft = (): ToolFormDraft => ({
    sourceToolId: null,
    title: "",
    description: "",
    category: DEFAULT_CATEGORY_CODE,
    keyword: "",
    query: "",
    code: "",
    provider: "",
    tokenToolId: "",
    execParamName: "parameter",
    execParamValue: "",
    execQuery: "",
});

export function toolToFormDraft(tool: ToolListItem): ToolFormDraft {
    const paramEntries = Object.entries(tool.default_parameters ?? {});
    const [paramName = "parameter", paramValue = ""] = paramEntries[0] ?? [];

    return {
        sourceToolId: tool.tool_id,
        title: tool.title,
        description: tool.description,
        category: tool.category || DEFAULT_CATEGORY_CODE,
        keyword: tool.keyword,
        query: tool.query,
        code: tool.code,
        provider: tool.provider,
        tokenToolId: tool.tokenToolId ?? "",
        execParamName: paramName,
        execParamValue: paramValue,
        execQuery: tool.recommendationQuery?.trim() ?? "",
    };
}

export type FormSliceState = {
    formDraft: ToolFormDraft;
    editorMode: ToolEditorMode;
    selectedToolId: string | null;
    formTitle: string;
    execQueryPlaceholder: string;
};

export type SelectToolOptions = {
    /** 생성 직후 등 — 목록 항목보다 우선 적용할 실행용 테스트 질의어 */
    execQuery?: string;
};

export type FinalizeAfterGenerateOptions = {
    /** 서버 반영 — 도구설명 */
    description?: string;
    /** 서버 반영 — code */
    code?: string;
    /** 서버 반영 — query_examples 기반 실행용 테스트 질의어 */
    execQuery?: string;
    /** 생성 직전 사용자 입력 — 도구 저장용 질의문 (서버값으로 덮어쓰지 않음) */
    preserveQuery?: string;
    caller?: string;
    lifecycleStatus?: ToolAssetStatus;
    assetPath?: string;
};

export type FormSliceActions = {
    selectTool: (tool: ToolListItem, options?: SelectToolOptions) => void;
    /** 생성 완료 후 — 사용자 입력 폼을 유지하고 선택·원본 캐시만 확정 */
    finalizeAfterGenerate: (toolId: string, options?: FinalizeAfterGenerateOptions) => void;
    createNewTool: () => void;
    patchFormField: (partial: Partial<ToolFormDraft>) => void;
    setFormDraft: (draft: ToolFormDraft) => void;
    setEditorMode: (mode: ToolEditorMode) => void;
    setSelectedToolId: (id: string | null) => void;
    bindExecPreview: (paramName: string, paramValue: string, recommendation?: string) => void;
    clearSelection: () => void;
};

export type FormSlice = FormSliceState & FormSliceActions;

export const createFormSlice: StateCreator<
    FormSlice & {
        captureOriginCache: (draft: ToolFormDraft) => void;
        resetDirtyGuard: () => void;
        resetExecPreview: (mode: "idle" | "selected" | "new", toolTitle?: string) => void;
        hydrateListTool: (toolId: string, status: ToolListItem["status"], caller?: string) => void;
        markAssetized: (assetPath: string) => void;
        resetLifecycle: () => void;
        toggleLeftPanel: (collapse: boolean) => void;
    },
    [],
    [],
    FormSlice
> = (set, get) => ({
    formDraft: emptyFormDraft(),
    editorMode: "idle",
    selectedToolId: null,
    formTitle: "도구 상세 설정 및 명세",
    execQueryPlaceholder: "실행용 테스트 질의어를 입력하거나 도구를 선택하십시오.",

    selectTool: (tool, options) => {
        const draft = toolToFormDraft(tool);
        const execQuery = options?.execQuery?.trim()
            || draft.execQuery.trim()
            || tool.recommendationQuery?.trim()
            || "";
        const resolvedDraft = execQuery ? { ...draft, execQuery } : draft;
        set({
            formDraft: resolvedDraft,
            selectedToolId: tool.tool_id,
            editorMode: "existing",
            formTitle: "도구 상세 설정 및 명세",
            execQueryPlaceholder: execQuery
                || tool.recommendationQuery
                || "추천 질의문을 불러오는 중...",
        });
        get().captureOriginCache(resolvedDraft);
        get().hydrateListTool(tool.tool_id, tool.status);
        get().resetExecPreview("selected", tool.title);
        get().toggleLeftPanel(true);
    },

    finalizeAfterGenerate: (toolId, options) => {
        const state = get();
        const suggestedExecQuery = options?.execQuery?.trim();
        const preserveQuery = options?.preserveQuery ?? state.formDraft.query;
        const nextDraft: ToolFormDraft = {
            ...state.formDraft,
            sourceToolId: toolId,
            query: preserveQuery,
            ...(options?.description?.trim()
                ? { description: options.description.trim() }
                : {}),
            ...(options?.code?.trim()
                ? { code: options.code.trim() }
                : {}),
        };

        set({
            formDraft: nextDraft,
            selectedToolId: toolId,
            editorMode: "existing",
            formTitle: "도구 상세 설정 및 명세",
            execQueryPlaceholder: suggestedExecQuery
                || state.execQueryPlaceholder,
        });
        get().captureOriginCache(nextDraft);

        const lifecycleStatus = options?.lifecycleStatus ?? "generated";
        if (lifecycleStatus === "assetized") {
            const assetPath = options?.assetPath?.trim();
            if (assetPath) {
                get().markAssetized(assetPath);
            } else {
                set({
                    lifecycleStage: "assetized",
                    pendingToolId: toolId,
                    isListAssetized: true,
                    callerScript: options?.caller ?? get().callerScript,
                });
            }
        } else {
            get().hydrateListTool(toolId, lifecycleStatus, options?.caller);
        }

        get().resetExecPreview("selected", nextDraft.title.trim());
    },

    createNewTool: () => {
        const draft: ToolFormDraft = {
            ...emptyFormDraft(),
            code: DEFAULT_NEW_TOOL_CODE,
            execParamValue: "test_value",
        };
        set({
            formDraft: draft,
            selectedToolId: null,
            editorMode: "new",
            formTitle: "신규 도구 정보 등록",
            execQueryPlaceholder: "새 도구를 생성하면 미리보기용 추천 질의문이 이곳에 반환됩니다.",
        });
        get().resetDirtyGuard();
        get().resetLifecycle();
        get().resetExecPreview("new");
    },

    patchFormField: (partial) => {
        set(state => ({ formDraft: { ...state.formDraft, ...partial } }));
    },

    setFormDraft: (draft) => set({ formDraft: draft }),

    setEditorMode: (mode) => set({ editorMode: mode }),

    setSelectedToolId: (id) => set({ selectedToolId: id }),

    bindExecPreview: (paramName, paramValue, recommendation) => {
        set(state => ({
            formDraft: {
                ...state.formDraft,
                execParamName: paramName,
                execParamValue: paramValue,
            },
            execQueryPlaceholder: recommendation?.trim()
                ?? state.execQueryPlaceholder,
        }));
    },

    clearSelection: () => {
        set({
            formDraft: emptyFormDraft(),
            selectedToolId: null,
            editorMode: "idle",
            formTitle: "도구 상세 설정 및 명세",
            execQueryPlaceholder: "실행용 테스트 질의어를 입력하거나 도구를 선택하십시오.",
        });
        get().resetDirtyGuard();
        get().resetLifecycle();
        get().resetExecPreview("idle");
    },
});
