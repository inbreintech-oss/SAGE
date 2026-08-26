import { pangeaze } from "@/features/data-analysis";
import type { PangeazePayload, PangeazeResponse } from "@/features/data-analysis";
import type { DataSource } from "@/features/data";
import { DATA_MODEL_SAVE_API_ENABLED } from "@/libs/stores/dataManagement/constants";

/** POST /data/save (추후) — Read 모드: 메타·sources만 저장, 스키마 미생성 */
export type SaveModelPayload = {
    name: string;
    description: string;
    sources: DataSource[];
    /** 기존 모델 갱신 시 */
    did?: string;
};

export type SaveModelResult = {
    did: string;
    status: string;
};

export class DataModelSaveNotEnabledError extends Error {
    constructor() {
        super("모델 저장 API는 아직 제공되지 않습니다. 스펙 업데이트 후 활성화됩니다.");
        this.name = "DataModelSaveNotEnabledError";
    }
}

/**
 * Read — 모델 메타·Pool(sources) 저장 (스키마 생성 없음).
 * DATA_MODEL_SAVE_API_ENABLED === true 및 POST /data/save 스펙 반영 후 구현.
 */
export async function saveModel(
    _payload: SaveModelPayload,
    _signal?: AbortSignal,
): Promise<SaveModelResult> {
    if (!DATA_MODEL_SAVE_API_ENABLED) {
        throw new DataModelSaveNotEnabledError();
    }
    // TODO: POST /api/data/save 연동
    throw new DataModelSaveNotEnabledError();
}

/** Pangeaze — Pool 기반 통합 스키마 생성 (현재 API: POST /data/pangeaze SSE) */
export type IntegrateModelPayload = PangeazePayload;

export async function integrateModel(
    payload: IntegrateModelPayload,
    signal?: AbortSignal,
): Promise<AsyncIterable<PangeazeResponse | string>> {
    return pangeaze(payload, signal);
}

/** @deprecated integrateModel 사용 */
export const saveDataModel = integrateModel;
