import type { ToolEditorMode, ToolLifecycleStage, UiButtonState } from "./types";

export function resolveUiButtonState(
    editorMode: ToolEditorMode,
    lifecycleStage: ToolLifecycleStage,
): UiButtonState {
    if (editorMode === "idle") return "unselected";
    if (editorMode === "new") return "new";
    if (lifecycleStage === "assetized") return "assetized";
    if (lifecycleStage === "generated") return "generated";
    return "unselected";
}

export type ButtonVisibility = {
    showReset: boolean;
    showDelete: boolean;
    showCreate: boolean;
    showModify: boolean;
    showSave: boolean;
    saveDisabled: boolean;
    canPreview: boolean;
    /** 도구 명세 폼(상단) — assetized 시 잠금. 미리보기 질의어는 제외 */
    formReadOnly: boolean;
};

export function resolveButtonVisibility(state: UiButtonState): ButtonVisibility {
    switch (state) {
        case "unselected":
            return {
                showReset: false,
                showDelete: false,
                showCreate: false,
                showModify: false,
                showSave: false,
                saveDisabled: true,
                canPreview: false,
                formReadOnly: false,
            };
        case "new":
            return {
                showReset: true,
                showDelete: false,
                showCreate: true,
                showModify: false,
                showSave: true,
                saveDisabled: true,
                canPreview: false,
                formReadOnly: false,
            };
        case "generated":
            return {
                showReset: true,
                showDelete: true,
                showCreate: false,
                showModify: true,
                showSave: true,
                saveDisabled: false,
                canPreview: true,
                formReadOnly: false,
            };
        case "assetized":
            return {
                showReset: true,
                showDelete: true,
                showCreate: false,
                showModify: false,
                showSave: true,
                saveDisabled: true,
                canPreview: true,
                formReadOnly: true,
            };
    }
}
