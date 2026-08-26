import { useShallow } from "zustand/react/shallow";
import { useToolManagementStore } from "../ToolManagementStore";
import { resolveButtonVisibility, resolveUiButtonState } from "./buttonState";
import { selectShowDeleteButton } from "./dirtyGuardSlice";
import { canExecTool } from "./lifecycleSlice";
import type { ToolListItem } from "./types";

export function useToolManagementState() {
    return useToolManagementStore(useShallow(s => ({
        tools: s.tools,
        listStatus: s.listStatus,
        listError: s.listError,
        formDraft: s.formDraft,
        editorMode: s.editorMode,
        selectedToolId: s.selectedToolId,
        formTitle: s.formTitle,
        execQueryPlaceholder: s.execQueryPlaceholder,
        isToolDirty: s.isToolDirty,
        lifecycleStage: s.lifecycleStage,
        pendingToolId: s.pendingToolId,
        callerScript: s.callerScript,
        assetPath: s.assetPath,
        isListAssetized: s.isListAssetized,
        validationErrors: s.validationErrors,
        traceLogs: s.traceLogs,
        jsonPreview: s.jsonPreview,
        visualResult: s.visualResult,
        execStatus: s.execStatus,
        consoleStatus: s.consoleStatus,
        leftPanelCollapsed: s.leftPanelCollapsed,
    })));
}

export function useToolManagementActions() {
    return useToolManagementStore(useShallow(s => ({
        setTools: s.setTools,
        setListStatus: s.setListStatus,
        setListError: s.setListError,
        selectTool: s.selectTool,
        finalizeAfterGenerate: s.finalizeAfterGenerate,
        createNewTool: s.createNewTool,
        patchFormField: s.patchFormField,
        evaluateToolDirty: s.evaluateToolDirty,
        resetToOrigin: s.resetToOrigin,
        attemptSaveTool: s.attemptSaveTool,
        attemptAssetizeTool: s.attemptAssetizeTool,
        attemptExecTool: s.attemptExecTool,
        markGenerated: s.markGenerated,
        markAssetized: s.markAssetized,
        bindExecPreview: s.bindExecPreview,
        setFormDraft: s.setFormDraft,
        setSelectedToolId: s.setSelectedToolId,
        setEditorMode: s.setEditorMode,
        clearSelection: s.clearSelection,
        appendTraceLog: s.appendTraceLog,
        appendTraceLogs: s.appendTraceLogs,
        setTraceLogs: s.setTraceLogs,
        setJsonPreview: s.setJsonPreview,
        setVisualResult: s.setVisualResult,
        setExecStatus: s.setExecStatus,
        setConsoleStatus: s.setConsoleStatus,
        clearExecState: s.clearExecState,
        resetExecPreview: s.resetExecPreview,
        captureOriginCache: s.captureOriginCache,
        resetDirtyGuard: s.resetDirtyGuard,
        resetLifecycle: s.resetLifecycle,
        toggleLeftPanel: s.toggleLeftPanel,
    })));
}

export function updateToolInList(toolId: string, patch: Partial<ToolListItem>) {
    const store = useToolManagementStore.getState();
    store.setTools(store.tools.map(t => (t.tool_id === toolId ? { ...t, ...patch } : t)));
}

export function useToolManagementDerived() {
    return useToolManagementStore(useShallow(s => {
        const uiButtonState = resolveUiButtonState(s.editorMode, s.lifecycleStage);
        const btn = resolveButtonVisibility(uiButtonState);

        return {
            uiButtonState,
            showReset: btn.showReset,
            showDelete: btn.showDelete,
            showCreate: btn.showCreate,
            showModify: btn.showModify,
            showSave: btn.showSave,
            saveDisabled: btn.saveDisabled,
            canPreview: btn.canPreview,
            formReadOnly: btn.formReadOnly,
            showDeleteButton: selectShowDeleteButton(s),
            canExec: canExecTool({
                lifecycleStage: s.lifecycleStage,
                pendingToolId: s.pendingToolId,
                selectedToolId: s.selectedToolId,
            }),
            lifecycleLabel:
                s.lifecycleStage === "generated" ? "생성등록"
                : s.lifecycleStage === "assetized" ? "자산등록"
                : null,
        };
    }));
}
