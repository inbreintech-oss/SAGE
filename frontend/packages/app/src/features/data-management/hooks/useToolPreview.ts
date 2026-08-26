import { useMutation } from "@tanstack/react-query";
import { previewToolResult, type ToolPreviewRequest } from "../services/toolExecService";

export function useToolPreview() {
    return useMutation({
        mutationFn: (req: ToolPreviewRequest) => previewToolResult(req),
    });
}
