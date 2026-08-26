import type { StateCreator } from "zustand";
import { poolsAreEqual } from "./poolFingerprint";
import type { PoolState } from "./poolSlice";

export type SaveAttemptResult =
    | { allowed: true }
    | { allowed: false; reason: "DUPLICATE_NAME" | "POOL_DIRTY" | "EMPTY_NAME" };

export type BuildSchemaAttemptResult =
    | { allowed: true }
    | { allowed: false; reason: "SCHEMA_ALREADY_EXISTS" | "EMPTY_NAME" | "EMPTY_POOL" };

export const DIRTY_MODAL_MESSAGE =
    "원천 데이터 Pool 정보가 변경되었습니다. 기존 보고서와의 연계 정보 유실을 방지하기 위해, " +
    "새로운 분석명과 분석설명으로 수정한 후 모델 저장을 진행해 주세요.";

export const DUPLICATE_NAME_MESSAGE =
    "이미 존재하는 분석명입니다. 다른 분석명을 입력해 주세요.";

export const SCHEMA_ALREADY_EXISTS_MESSAGE =
    "이미 생성된 통합 스키마가 있으므로 생성이 제한됩니다.";

export type DirtyGuardState = {
    loadedModelName: string | null;
    loadedModelDid: string | null;
    isPoolDirty: boolean;
    hasActiveSchema: boolean;
    isNameDuplicate: boolean;
    dirtyModalOpen: boolean;
};

export type DirtyGuardActions = {
    captureBaseline: (did: string, name: string) => void;
    evaluatePoolDirty: () => void;
    evaluateName: (name: string, existingNames: string[]) => void;
    attemptSave: (analysisName: string) => SaveAttemptResult;
    attemptBuildSchema: () => BuildSchemaAttemptResult;
    setHasActiveSchema: (value: boolean) => void;
    openDirtyModal: () => void;
    closeDirtyModal: () => void;
    resetDirtyGuard: () => void;
};

type DirtyGuardSlice = DirtyGuardState & DirtyGuardActions;

export const createDirtyGuardSlice: StateCreator<
    DirtyGuardSlice & PoolState & { analysisName: string },
    [],
    [],
    DirtyGuardSlice
> = (set, get) => ({
    loadedModelName: null,
    loadedModelDid: null,
    isPoolDirty: false,
    hasActiveSchema: false,
    isNameDuplicate: false,
    dirtyModalOpen: false,

    captureBaseline: (did, name) =>
        set({
            loadedModelDid: did,
            loadedModelName: name,
            isPoolDirty: false,
            isNameDuplicate: false,
            dirtyModalOpen: false,
        }),

    evaluatePoolDirty: () => {
        const { loadedModelDid, poolItems, baselinePoolItems } = get();
        if (!loadedModelDid) {
            set({ isPoolDirty: false });
            return;
        }
        set({ isPoolDirty: !poolsAreEqual(poolItems, baselinePoolItems) });
    },

    evaluateName: (name, existingNames) => {
        const trimmed = name.trim();
        const { loadedModelDid, loadedModelName } = get();
        const others = loadedModelDid
            ? existingNames.filter(n => n !== loadedModelName)
            : existingNames;
        set({ isNameDuplicate: trimmed.length > 0 && others.some(n => n === trimmed) });
    },

    attemptSave: (analysisName) => {
        const { isPoolDirty, isNameDuplicate, loadedModelName } = get();
        const trimmed = analysisName.trim();

        if (!trimmed) return { allowed: false, reason: "EMPTY_NAME" };
        if (isNameDuplicate) return { allowed: false, reason: "DUPLICATE_NAME" };

        if (isPoolDirty && trimmed === loadedModelName) {
            set({ dirtyModalOpen: true });
            return { allowed: false, reason: "POOL_DIRTY" };
        }
        return { allowed: true };
    },

    attemptBuildSchema: () => {
        const {
            loadedModelDid,
            hasActiveSchema,
            isPoolDirty,
            analysisName,
            poolItems,
        } = get();

        if (!analysisName.trim()) {
            return { allowed: false, reason: "EMPTY_NAME" };
        }
        if (poolItems.length === 0) {
            return { allowed: false, reason: "EMPTY_POOL" };
        }

        if (loadedModelDid && hasActiveSchema && !isPoolDirty) {
            return { allowed: false, reason: "SCHEMA_ALREADY_EXISTS" };
        }

        return { allowed: true };
    },

    setHasActiveSchema: (value) => set({ hasActiveSchema: value }),

    openDirtyModal: () => set({ dirtyModalOpen: true }),
    closeDirtyModal: () => set({ dirtyModalOpen: false }),

    resetDirtyGuard: () =>
        set({
            loadedModelName: null,
            loadedModelDid: null,
            isPoolDirty: false,
            hasActiveSchema: false,
            isNameDuplicate: false,
            dirtyModalOpen: false,
        }),
});

export function selectCanSave(
    analysisName: string,
    guard: DirtyGuardState,
): boolean {
    const trimmed = analysisName.trim();
    if (!trimmed || guard.isNameDuplicate) return false;
    if (guard.isPoolDirty && trimmed === (guard.loadedModelName ?? "")) return false;
    return true;
}

export function selectCanBuildSchema(guard: DirtyGuardState): boolean {
    if (!guard.loadedModelDid) return true;
    if (!guard.hasActiveSchema) return true;
    return guard.isPoolDirty;
}
