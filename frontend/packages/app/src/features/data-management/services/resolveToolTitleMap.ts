import type { DataSource } from "@/features/data";
import { toolInfo } from "@/features/tool/api";
import {
    isToolDataSource,
    resolveToolSourceId,
} from "@/libs/stores/dataManagement/poolSlice";

/**
 * 데이터 모델 sources[] 의 tool 항목 displayName 복원용 title map.
 * 1) 기존 catalog 2) GET /tool/info 3) source.origin (`/` 포함 전체 보존) 순으로 조회.
 */
export async function buildToolTitleMap(
    sources: DataSource[] | undefined,
    catalog: Record<string, string> = {},
): Promise<Record<string, string>> {
    const map = { ...catalog };
    const toolSources = (sources ?? []).filter(isToolDataSource);

    await Promise.all(toolSources.map(async (src) => {
        const id = resolveToolSourceId(src);
        if (!id || map[id]) return;

        try {
            const res = await toolInfo(id);
            if (res.success) {
                const title = res.result?.title?.trim();
                if (title) {
                    map[id] = title;
                    return;
                }
            }
        } catch {
            // toolInfo 실패 시 origin 폴백
        }

        const origin = src.origin?.trim();
        if (origin && origin !== id) {
            map[id] = origin;
        }
    }));

    return map;
}
