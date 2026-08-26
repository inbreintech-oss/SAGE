import { useMemo } from "react";
import { useCompletedDataList } from "@/features/data";
import { usePublishedReportList } from "@/features/report-management/hooks";
import { useTool } from "@/features/tool";
import { buildDashboardAggregates } from "./aggregates";
import type { DashboardAggregates } from "./types";

export function useDashboardData() {
    const modelsQuery = useCompletedDataList();
    const reportsQuery = usePublishedReportList();
    const toolsQuery = useTool();

    const models = modelsQuery.data ?? [];
    const reports = reportsQuery.data ?? [];
    const tools = toolsQuery.data?.result ?? [];

    const aggregates = useMemo<DashboardAggregates>(
        () => buildDashboardAggregates(models, reports, tools),
        [models, reports, tools],
    );

    const isLoading = modelsQuery.isLoading || reportsQuery.isLoading || toolsQuery.isLoading;
    const isError = modelsQuery.isError || reportsQuery.isError || toolsQuery.isError;
    const hasFetched =
        modelsQuery.data !== undefined
        || reportsQuery.data !== undefined
        || toolsQuery.data !== undefined;

    const refetch = () => {
        void modelsQuery.refetch();
        void reportsQuery.refetch();
        void toolsQuery.refetch();
    };

    return {
        aggregates,
        isLoading,
        isError,
        hasFetched,
        refetch,
    };
}
