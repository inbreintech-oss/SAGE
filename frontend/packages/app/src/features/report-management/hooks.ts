import { type QueryClient, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queries as toolQueries } from "@/features/tool/queries";
import { recommendTools, type Tool } from "@/features/tool";
import {
    execReportSync,
    generateReportSync,
    publishReport,
    reportListQuery,
    type GenerateReportSyncPayload,
} from "./api";
import type { ExecReportPayload, PublishReportPayload } from "./reportListTypes";

export const reportManagementKeys = {
    all: ["report-management"] as const,
    publishedList: () => [...reportManagementKeys.all, "published-list"] as const,
    recommendTools: (did: string, category: string) =>
        [...reportManagementKeys.all, "recommend-tools", did, category] as const,
};

export type RecommendedToolItem = {
    tool_id: string;
    title: string;
    description?: string;
};

async function fetchRecommendedTools(
    did: string,
    toolCategory: string,
    queryClient: QueryClient,
): Promise<RecommendedToolItem[]> {
    const ids = await recommendTools({ did, tool_category: toolCategory });
    if (ids.length === 0) return [];

    let catalog: Tool[] = [];
    try {
        const listRes = await queryClient.fetchQuery(toolQueries.toolList());
        catalog = listRes.result ?? [];
    } catch {
        catalog = [];
    }

    return ids.map(id => {
        const found = catalog.find(t => t.tool_id === id);
        return found
            ? { tool_id: found.tool_id, title: found.title, description: found.description }
            : { tool_id: id, title: id };
    });
}

export function usePublishedReportList() {
    return useQuery({
        queryKey: reportManagementKeys.publishedList(),
        queryFn: () => reportListQuery({ status: ["published"] }),
        staleTime: 30_000,
    });
}

export function useRecommendedTools(did: string | null | undefined, toolCategory: string) {
    const queryClient = useQueryClient();
    return useQuery({
        queryKey: reportManagementKeys.recommendTools(did ?? "", toolCategory),
        queryFn: () => fetchRecommendedTools(did!, toolCategory, queryClient),
        enabled: Boolean(did),
        staleTime: 60_000,
    });
}

export function useGenerateReport() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (payload: GenerateReportSyncPayload) => generateReportSync(payload),
        onSuccess: () => {
            void queryClient.invalidateQueries({ queryKey: reportManagementKeys.publishedList() });
        },
    });
}

export function usePublishReport() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (payload: PublishReportPayload) => publishReport(payload),
        onSuccess: () => {
            void queryClient.invalidateQueries({ queryKey: reportManagementKeys.publishedList() });
        },
    });
}

export function useExecReport() {
    return useMutation({
        mutationFn: (payload: ExecReportPayload) => execReportSync(payload),
    });
}
