import {useMutation, useQuery} from "@tanstack/react-query";
import {queries} from "./queries";
import {toolExec, type ToolExecPayload} from "./api";

export function useTool() {
    return useQuery({
        ...queries.toolList(),
    });
}

export function useToolInfo(tool_id: string) {
    return useQuery({
        ...queries.toolInfo(tool_id),
    });
}

export function useToolExec() {
    return useMutation({
        mutationFn: (payload: ToolExecPayload) => toolExec(payload),
    });
}