import type { StateCreator } from "zustand";
import {
    ALREADY_SAVED_MESSAGE,
    DUPLICATE_TITLE_MESSAGE,
    EXEC_NO_SAVE_POINT_MESSAGE,
    SCHEMA_ALREADY_EXISTS_MESSAGE,
} from "./constants";
import { canExecTool } from "./lifecycleSlice";
import { draftsAreEqual } from "./toolFingerprint";
import type {
    AssetizeAttemptResult,
    ExecAttemptResult,
    OriginSelectedToolCache,
    RequiredFormField,
    SaveAttemptResult,
    ToolEditorMode,
    ToolFormDraft,
    ToolLifecycleStage,
    ToolListItem,
} from "./types";

export type DirtyGuardSliceState = {
    originSelectedToolCache: OriginSelectedToolCache | null;
    isToolDirty: boolean;
    validationErrors: Partial<Record<RequiredFormField, string>>;
};

export type DirtyGuardSliceActions = {
    captureOriginCache: (draft: ToolFormDraft) => void;
    evaluateToolDirty: () => void;
    resetToOrigin: () => { changed: boolean };
    attemptSaveTool: (tools: ToolListItem[]) => SaveAttemptResult;
    attemptAssetizeTool: (tools: ToolListItem[]) => AssetizeAttemptResult;
    attemptExecTool: () => ExecAttemptResult;
    setValidationErrors: (errors: Partial<Record<RequiredFormField, string>>) => void;
    clearValidationErrors: () => void;
    resetDirtyGuard: () => void;
};

export type DirtyGuardSlice = DirtyGuardSliceState & DirtyGuardSliceActions;

function validateRequired(draft: ToolFormDraft): Partial<Record<RequiredFormField, string>> {
    const errors: Partial<Record<RequiredFormField, string>> = {};
    if (!draft.title.trim()) errors.title = "도구명을 입력해 주세요.";
    if (!draft.description.trim()) errors.description = "도구설명을 입력해 주세요.";
    if (!draft.category.trim()) errors.category = "도구 카테고리를 선택해 주세요.";
    if (!draft.keyword.trim()) errors.keyword = "연관 키워드를 입력해 주세요.";
    if (!draft.query.trim()) errors.query = "도구 저장용 질의문을 입력해 주세요.";
    return errors;
}

function isTitleDuplicate(
    title: string,
    tools: ToolListItem[],
    excludeToolId?: string | null,
): boolean {
    const normalized = title.trim().toLowerCase();
    return tools.some(t =>
        t.tool_id !== excludeToolId
        && t.title.trim().toLowerCase() === normalized,
    );
}

function isSchemaLocked(
    lifecycleStage: ToolLifecycleStage,
    isToolDirty: boolean,
): boolean {
    return lifecycleStage === "assetized" && !isToolDirty;
}

export const createDirtyGuardSlice: StateCreator<
    DirtyGuardSlice & {
        formDraft: ToolFormDraft;
        editorMode: ToolEditorMode;
        selectedToolId: string | null;
        lifecycleStage: ToolLifecycleStage;
        pendingToolId: string | null;
        execQueryPlaceholder: string;
        isListAssetized: boolean;
        setFormDraft: (draft: ToolFormDraft) => void;
        setEditorMode: (mode: ToolEditorMode) => void;
    },
    [],
    [],
    DirtyGuardSlice
> = (set, get) => ({
    originSelectedToolCache: null,
    isToolDirty: false,
    validationErrors: {},

    captureOriginCache: (draft) =>
        set({
            originSelectedToolCache: structuredClone(draft),
            isToolDirty: false,
            validationErrors: {},
        }),

    evaluateToolDirty: () => {
        const { originSelectedToolCache, formDraft, editorMode } = get();
        if (!originSelectedToolCache || editorMode === "new" || editorMode === "idle") {
            set({ isToolDirty: false });
            return;
        }
        const dirty = !draftsAreEqual(formDraft, originSelectedToolCache);
        set({
            isToolDirty: dirty,
            editorMode: dirty ? "clone" : "existing",
        });
    },

    resetToOrigin: () => {
        const { originSelectedToolCache, formDraft } = get();
        if (!originSelectedToolCache) return { changed: false };
        if (draftsAreEqual(formDraft, originSelectedToolCache)) {
            return { changed: false };
        }
        const restored = structuredClone(originSelectedToolCache);
        set({
            formDraft: restored,
            isToolDirty: false,
            editorMode: "existing",
            validationErrors: {},
        });
        return { changed: true };
    },

    attemptSaveTool: (tools) => {
        const { formDraft, editorMode, isToolDirty, lifecycleStage, pendingToolId, selectedToolId } = get();
        const excludeToolId = editorMode === "clone"
            ? null
            : (pendingToolId ?? selectedToolId);
        const errors = validateRequired(formDraft);
        if (Object.keys(errors).length > 0) {
            set({ validationErrors: errors });
            return {
                allowed: false,
                reason: "VALIDATION_FAILED",
                message: "모든 필수 입력 필드(*)를 작성해 주세요.",
                invalidFields: Object.keys(errors) as RequiredFormField[],
            };
        }
        set({ validationErrors: {} });

        if (isSchemaLocked(lifecycleStage, isToolDirty)) {
            return {
                allowed: false,
                reason: "SCHEMA_ALREADY_EXISTS",
                message: SCHEMA_ALREADY_EXISTS_MESSAGE,
            };
        }

        if (lifecycleStage === "generated" && !isToolDirty && editorMode !== "clone") {
            return {
                allowed: false,
                reason: "ALREADY_SAVED",
                message: ALREADY_SAVED_MESSAGE,
            };
        }

        if (editorMode === "existing" && !isToolDirty) {
            return {
                allowed: false,
                reason: "SCHEMA_ALREADY_EXISTS",
                message: SCHEMA_ALREADY_EXISTS_MESSAGE,
            };
        }

        if (isTitleDuplicate(formDraft.title, tools, excludeToolId)) {
            return {
                allowed: false,
                reason: "DUPLICATE_TITLE",
                message: DUPLICATE_TITLE_MESSAGE,
            };
        }

        const pipeline = editorMode === "clone" ? "CLONE" : "CREATE";
        return { allowed: true, pipeline };
    },

    attemptAssetizeTool: (tools) => {
        const { formDraft, isToolDirty, lifecycleStage, pendingToolId, selectedToolId } = get();
        const excludeToolId = pendingToolId ?? selectedToolId;
        const errors = validateRequired(formDraft);
        if (Object.keys(errors).length > 0) {
            set({ validationErrors: errors });
            return {
                allowed: false,
                reason: "VALIDATION_FAILED",
                message: "모든 필수 입력 필드(*)를 작성해 주세요.",
                invalidFields: Object.keys(errors) as RequiredFormField[],
            };
        }
        set({ validationErrors: {} });

        if (isSchemaLocked(lifecycleStage, isToolDirty)) {
            return {
                allowed: false,
                reason: "SCHEMA_ALREADY_EXISTS",
                message: SCHEMA_ALREADY_EXISTS_MESSAGE,
            };
        }

        if (isTitleDuplicate(formDraft.title, tools, excludeToolId)) {
            return {
                allowed: false,
                reason: "DUPLICATE_TITLE",
                message: DUPLICATE_TITLE_MESSAGE,
            };
        }

        return { allowed: true };
    },

    attemptExecTool: () => {
        const state = get();

        if (!canExecTool({
            lifecycleStage: state.lifecycleStage,
            pendingToolId: state.pendingToolId,
            selectedToolId: state.selectedToolId,
        })) {
            return {
                allowed: false,
                reason: "NO_SAVE_POINT",
                message: EXEC_NO_SAVE_POINT_MESSAGE,
            };
        }

        if (!state.formDraft.execQuery.trim()) {
            return {
                allowed: false,
                reason: "EMPTY_PARAM",
                message: "실행용 테스트 질의어를 입력해 주세요.",
            };
        }

        return { allowed: true };
    },

    setValidationErrors: (errors) => set({ validationErrors: errors }),

    clearValidationErrors: () => set({ validationErrors: {} }),

    resetDirtyGuard: () =>
        set({
            originSelectedToolCache: null,
            isToolDirty: false,
            validationErrors: {},
        }),
});

export function selectShowDeleteButton(state: {
    selectedToolId: string | null;
    editorMode: ToolEditorMode;
}): boolean {
    return state.selectedToolId !== null && state.editorMode !== "new";
}
