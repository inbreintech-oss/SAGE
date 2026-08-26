import {queryOptions} from "@tanstack/react-query";
import {toolInfo, toolList} from "@/features/tool/api.ts";

export const keys = {
    all: () => ["tool"],
    list: () => ["tool", "list"],
    info: (tool_id: string) => ["tool", "info", tool_id],
} as const

export const queries = {
    toolList: () =>
        queryOptions({
            queryKey: keys.list(),
            queryFn: () => toolList(),
            staleTime: 60_000,
        }),
    toolInfo: (tool_id: string) =>
        queryOptions({
            queryKey: keys.info(tool_id),
            queryFn: () => toolInfo(tool_id),
            enabled: (tool_id?.length ?? 0) > 0
        })
} as const;