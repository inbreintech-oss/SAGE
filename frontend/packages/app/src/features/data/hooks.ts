import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queries } from "./queries";
import { deleteData } from "./api";
import { selectCompletedDataList } from "./selectors";

export function useDataList() {
    const { data, isLoading, isPending, isError, error, refetch } = useQuery({
        ...queries.getDataList()
    });

    return {
        data,
        isLoading: isLoading || isPending,
        isError,
        error,
        refetch,
    };
}

/**
 * completed 분석모델 — useDataList 캐시를 클라이언트 필터로 파생 (별도 API 호출 없음)
 */
export function useCompletedDataList() {
    const { data, isLoading, isPending, isError, error, refetch } = useDataList();
    const completedData = useMemo(() => selectCompletedDataList(data), [data]);

    return {
        data: completedData,
        isLoading: isLoading || isPending,
        isError,
        error,
        refetch,
    };
}

export const useReportPickerDataList = useCompletedDataList;

/* ── 데이터셋 삭제 Mutation ── */
export function useDeleteData() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (did: string) => deleteData(did),
        onSuccess: () => {
            // 삭제 성공 후 목록 캐시 무효화 → 자동 재조회
            queryClient.invalidateQueries({ queryKey: ["data", "list"] });
        },
    });
}
