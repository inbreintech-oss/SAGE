import { toolExec } from "@/features/tool/api";

export type ToolPreviewRequest = {
    toolId: string;
    query: string;
    sandboxDefaults?: Record<string, unknown>;
};

export async function previewToolResult(req: ToolPreviewRequest): Promise<unknown> {
    const response = await toolExec({
        tools: [req.toolId],
        query: req.query.trim(),
    });
    if (!response.success) {
        throw new Error(response.error ?? "도구 실행에 실패했습니다.");
    }
    return response.result;
}
