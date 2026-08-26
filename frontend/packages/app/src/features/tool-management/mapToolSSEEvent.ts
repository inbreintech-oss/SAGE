import type { SSEEventData } from "@/features/Utils";

function resolveMessage(event: SSEEventData): string | null {
    if (typeof event.msg === "string" && event.msg.trim()) return event.msg.trim();
    if (typeof event.message === "string" && event.message.trim()) return event.message.trim();
    return null;
}

/** Tool generate/update SSE 이벤트 → 트랜잭션 로그 한 줄 */
export function mapToolSSEEventToTraceLine(event: SSEEventData): string | null {
    const msg = resolveMessage(event);
    const type = String(event.eventType ?? "unknown").toLowerCase();

    if (type === "completed" && !msg) return null;

    switch (type) {
        case "system":
        case "init":
        case "started":
            return msg ? `[SYSTEM] ${msg}` : null;
        case "success":
        case "completed":
            return msg ? `[SUCCESS] ${msg}` : "[SUCCESS] Process completed.";
        case "error":
        case "failed":
            return msg ? `[ERROR] ${msg}` : "[ERROR] Process failed.";
        case "warn":
        case "warning":
            return msg ? `[WARN] ${msg}` : null;
        case "trace":
            return msg ? `[TRACE] ${msg}` : null;
        default:
            return msg ? `[INFO] ${msg}` : null;
    }
}
