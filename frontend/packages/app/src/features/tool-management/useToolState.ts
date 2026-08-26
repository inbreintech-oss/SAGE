import {
    useToolManagementActions,
    useToolManagementDerived,
    useToolManagementState,
} from "@/libs/stores/toolManagement/useToolManagementSelectors";
import type { UiButtonState } from "@/libs/stores/toolManagement/types";
import type { ButtonVisibility } from "@/libs/stores/toolManagement/buttonState";

export type ToolStateButtons = ButtonVisibility;

export type UseToolStateResult = ReturnType<typeof useToolManagementState> & {
    uiButtonState: UiButtonState;
    buttons: ToolStateButtons;
    formReadOnly: boolean;
    canExec: boolean;
    showDeleteButton: boolean;
    lifecycleLabel: string | null;
};

/**
 * 도구(API) 관리 화면 상태 머신 훅.
 * Zustand store + UI 버튼 매트릭스(unselected → new → generated → assetized)를 단일 진입점으로 노출합니다.
 *
 * 검색(filter)은 ToolListPanel 로컬 state — 전역 store 구독과 분리합니다.
 */
export function useToolState() {
    const state = useToolManagementState();
    const derived = useToolManagementDerived();
    const actions = useToolManagementActions();

    const buttons: ToolStateButtons = {
        showReset: derived.showReset,
        showDelete: derived.showDelete,
        showCreate: derived.showCreate,
        showModify: derived.showModify,
        showSave: derived.showSave,
        saveDisabled: derived.saveDisabled,
        canPreview: derived.canPreview,
        formReadOnly: derived.formReadOnly,
    };

    return {
        ...state,
        actions,
        uiButtonState: derived.uiButtonState,
        buttons,
        formReadOnly: derived.formReadOnly,
        canExec: derived.canExec,
        showDeleteButton: derived.showDeleteButton,
        lifecycleLabel: derived.lifecycleLabel,
    };
}
