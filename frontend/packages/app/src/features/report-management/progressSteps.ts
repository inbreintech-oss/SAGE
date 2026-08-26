/**
 * Plan task SSE 생명주기 → 운영자용 생성 진행 스냅샷
 * waiting → generating → executing/progress → executed
 * retrying → generating 부터 재개
 */

export type TaskLifecyclePhase =
    | "pending"
    | "waiting"
    | "generating"
    | "executing"
    | "executed"
    | "retrying"
    | "failed";

export type ReportTaskProgress = {
    taskId: string;
    title: string;
    taskType?: string;
    phase: TaskLifecyclePhase;
    lastMessage: string;
    retryCount: number;
    order: number;
};

export type GenerationProgressPhase = "idle" | "running" | "completed" | "failed";

export type ReportProgressSnapshot = {
    tasks: ReportTaskProgress[];
    activeTaskId: string | null;
    logs: string[];
};

export type ProgressStepStatus = "pending" | "active" | "done" | "error";

/** UI 행 — task 1줄 */
export type ProgressStep = {
    id: string;
    label: string;
    detail: string;
    status: ProgressStepStatus;
    phaseLabel: string;
};

export type GenerationProgressView = {
    phase: GenerationProgressPhase;
    headline: string;
    currentMessage: string;
    steps: ProgressStep[];
    completedCount: number;
    totalCount: number;
};

const TASK_TYPE_LABEL: Record<string, string> = {
    load: "데이터",
    analyze: "분석",
    visual: "차트",
    visualize: "차트",
    narrative: "본문",
    release: "검토",
};

/** 섹션(phase) 배지 — 운영자용 */
const PHASE_LABEL: Record<TaskLifecyclePhase, string> = {
    pending: "대기",
    waiting: "준비 중",
    generating: "구성 준비",
    executing: "작성 중",
    executed: "완료",
    retrying: "다시 시도",
    failed: "실패",
};

const ACTIVE_PHASES: ReadonlySet<TaskLifecyclePhase> = new Set([
    "waiting",
    "generating",
    "executing",
    "retrying",
]);

/** msg [제목] 추출 시 기술 태그로 오인하지 않도록 제외 */
const TECH_BRACKET_TAGS = new Set([
    "mcp",
    "pangea",
    "plan",
    "load",
    "analyze",
    "visual",
    "chart",
    "narrative",
    "release",
    "agg",
    "quality",
    "qa",
]);

export function createEmptyProgressSnapshot(): ReportProgressSnapshot {
    return { tasks: [], activeTaskId: null, logs: [] };
}

function typeSubtitle(taskType?: string): string {
    if (!taskType) return "";
    return TASK_TYPE_LABEL[taskType.toLowerCase()] ?? "";
}

function extractBracketTitle(msg: string): string | null {
    const m = msg.match(/\[([^\]]+)\]/);
    const title = m?.[1]?.trim();
    if (!title) return null;
    if (TECH_BRACKET_TAGS.has(title.toLowerCase())) return null;
    // 경로·코드성 짧은 영문 토큰 제외
    if (/^[a-z][a-z0-9_-]{0,24}$/i.test(title) && !/[가-힣]/.test(title)) {
        if (TECH_BRACKET_TAGS.has(title.toLowerCase())) return null;
    }
    return title;
}

/** progress msg에서 (3/28), 3/28, N건 등만 추출 */
export function extractProgressCount(raw: string): string | null {
    const fraction = raw.match(/\((\d+\s*\/\s*\d+)\)/) ?? raw.match(/\b(\d+\s*\/\s*\d+)\b/);
    if (fraction) return fraction[1].replace(/\s+/g, "");
    const count = raw.match(/(\d+)\s*건/);
    if (count) return `${count[1]}건`;
    return null;
}

/**
 * SSE 원문 → 화면용 한 줄 (도메인 중립)
 * 기술 토큰은 제거하고, 있으면 진행 수치만 유지
 */
export function toUserFacingProgressLine(raw: string, sectionTitle?: string): string {
    const text = raw.trim();
    if (!text) {
        return sectionTitle ? `「${sectionTitle}」 섹션을 진행하고 있습니다` : "섹션을 진행하고 있습니다";
    }

    const count = extractProgressCount(text);
    const lower = text.toLowerCase();

    if (/upstream|완료\s*대기/i.test(text)) {
        return "앞선 섹션이 끝나기를 기다리고 있습니다";
    }
    if (/\bmcp\b|tool_path|tool_name/i.test(lower)) {
        return count
            ? `외부 정보를 확인하고 있습니다 (${count})`
            : "외부 정보를 확인하고 있습니다";
    }
    if (/pangea|to_pandas|스키마|데이터\s*로드|불러/i.test(text)) {
        return count
            ? `분석 데이터를 불러오고 있습니다 (${count})`
            : "분석 데이터를 불러오고 있습니다";
    }
    if (/universe|티커|종목\s*목록|분석\s*대상/i.test(text)) {
        return count
            ? `분석 대상을 정리하고 있습니다 (${count})`
            : "분석 대상을 정리하고 있습니다";
    }
    if (/executor|codegen|소스\s*생성|\.py|bytes/i.test(lower) || /소스/.test(text)) {
        return "섹션 준비 작업을 진행하고 있습니다";
    }
    if (/산출\s*key|update_task|queue_update|ctx\.save|board/i.test(lower)) {
        return "이 섹션 결과를 정리하고 있습니다";
    }
    if (/layout|echart|chart|card\b|블록|표\s*구성/i.test(lower) || /차트|문단/.test(text)) {
        return count
            ? `보고서 구성 요소를 배치하고 있습니다 (${count})`
            : "보고서 구성 요소를 배치하고 있습니다";
    }
    if (/재시도|retry|문법\s*오류|traceback/i.test(lower)) {
        return "섹션을 다시 준비하고 있습니다";
    }
    if (/실행\s*완료|완료\s*—/i.test(text)) {
        return "이 섹션을 마쳤습니다";
    }
    if (/실행\s*실패|실패:|연결\s*오류/i.test(text)) {
        return sectionTitle
            ? `「${sectionTitle}」 섹션을 완성하지 못했습니다`
            : "이 섹션을 완성하지 못했습니다";
    }

    // 알 수 없는 progress — 원문 금지, 섹션명 + 수치만
    if (count) {
        return sectionTitle
            ? `「${sectionTitle}」 섹션을 진행하고 있습니다 (${count})`
            : `섹션을 진행하고 있습니다 (${count})`;
    }
    return sectionTitle
        ? `「${sectionTitle}」 섹션을 진행하고 있습니다`
        : "섹션을 진행하고 있습니다";
}

/** phase 기준 고정 문구 (메인 UI) — SSE msg 비노출 */
export function toUserFacingPhaseMessage(
    phase: TaskLifecyclePhase,
    sectionTitle: string,
    options?: { retryCount?: number; rawProgressMsg?: string },
): string {
    const name = sectionTitle.trim() || "섹션";
    switch (phase) {
        case "pending":
            return `「${name}」 섹션 대기 중`;
        case "waiting":
            return "이전 섹션이 끝날 때까지 준비 중";
        case "generating":
            return `「${name}」 섹션을 구성하기 위한 작업을 준비하고 있습니다`;
        case "executing":
            if (options?.rawProgressMsg?.trim()) {
                return toUserFacingProgressLine(options.rawProgressMsg, name);
            }
            return `「${name}」 섹션 내용을 만들고 있습니다`;
        case "executed":
            return `「${name}」 섹션을 마쳤습니다`;
        case "retrying": {
            const n = options?.retryCount && options.retryCount > 0
                ? ` (${options.retryCount}회)`
                : "";
            return `문제가 있어 「${name}」 섹션을 다시 준비하고 있습니다${n}`;
        }
        case "failed":
            return `「${name}」 섹션을 완성하지 못했습니다`;
        default:
            return `「${name}」 섹션을 진행하고 있습니다`;
    }
}

function resolveEventName(raw: Record<string, unknown>): string {
    const fromType = typeof raw.eventType === "string" ? raw.eventType.trim() : "";
    const fromEvent = typeof raw.event === "string" ? raw.event.trim() : "";
    return (fromType || fromEvent || "").toLowerCase();
}

function resolveTaskId(raw: Record<string, unknown>): string | null {
    if (typeof raw.task_id === "string" && raw.task_id.trim()) return raw.task_id.trim();
    return null;
}

function resolveMsg(raw: Record<string, unknown>): string {
    if (typeof raw.msg === "string" && raw.msg.trim()) return raw.msg.trim();
    if (typeof raw.message === "string" && raw.message.trim()) return raw.message.trim();
    return "";
}

function upsertTask(
    tasks: ReportTaskProgress[],
    patch: Partial<ReportTaskProgress> & { taskId: string },
): ReportTaskProgress[] {
    const idx = tasks.findIndex(t => t.taskId === patch.taskId);
    if (idx < 0) {
        const next: ReportTaskProgress = {
            taskId: patch.taskId,
            title: patch.title ?? patch.taskId,
            taskType: patch.taskType,
            phase: patch.phase ?? "pending",
            lastMessage: patch.lastMessage ?? "",
            retryCount: patch.retryCount ?? 0,
            order: patch.order ?? tasks.length,
        };
        return [...tasks, next];
    }
    const prev = tasks[idx];
    const updated: ReportTaskProgress = {
        ...prev,
        ...patch,
        title: patch.title?.trim() ? patch.title : prev.title,
        taskType: patch.taskType ?? prev.taskType,
        lastMessage: patch.lastMessage !== undefined ? patch.lastMessage : prev.lastMessage,
        retryCount: patch.retryCount ?? prev.retryCount,
        order: prev.order,
    };
    const copy = tasks.slice();
    copy[idx] = updated;
    return copy;
}

/** plan.tasks 로 뼈대 hydrate (이벤트보다 먼저 올 때) */
export function hydrateProgressFromPlan(
    snapshot: ReportProgressSnapshot,
    plan: { tasks?: Array<{ task_id?: string; title?: string; type?: string }> } | null | undefined,
): ReportProgressSnapshot {
    const planTasks = plan?.tasks;
    if (!planTasks?.length) return snapshot;

    let tasks = snapshot.tasks.slice();
    planTasks.forEach((pt, i) => {
        const tid = pt.task_id?.trim();
        if (!tid) return;
        tasks = upsertTask(tasks, {
            taskId: tid,
            title: pt.title?.trim() || tid,
            taskType: pt.type,
            phase: tasks.find(t => t.taskId === tid)?.phase ?? "pending",
            order: i,
        });
    });
    tasks = [...tasks].sort((a, b) => a.order - b.order);
    return { ...snapshot, tasks };
}

/** SSE 이벤트 1건 반영 */
export function applyProgressEvent(
    snapshot: ReportProgressSnapshot,
    raw: Record<string, unknown>,
): ReportProgressSnapshot {
    const eventName = resolveEventName(raw);
    const msg = resolveMsg(raw);
    const taskId = resolveTaskId(raw);
    const taskType = typeof raw.task_type === "string" ? raw.task_type : undefined;
    const titleFromMsg = msg ? extractBracketTitle(msg) : null;

    let logs = snapshot.logs;
    if (msg) {
        logs = [...snapshot.logs, msg];
    } else if (eventName && eventName !== "unknown") {
        logs = [...snapshot.logs, `[${eventName}]`];
    }

    if (!taskId) {
        return { ...snapshot, logs };
    }

    let phase: TaskLifecyclePhase | undefined;
    let retryBump = false;

    switch (eventName) {
        case "waiting":
            phase = "waiting";
            break;
        case "generating":
        case "generated":
            phase = "generating";
            break;
        case "executing":
        case "progress":
            phase = "executing";
            break;
        case "executed":
            phase = "executed";
            break;
        case "retrying":
            phase = "retrying";
            retryBump = true;
            break;
        case "failed":
        case "error":
            phase = "failed";
            break;
        default:
            // task_id 있는 알 수 없는 이벤트 — 메시지만 갱신
            break;
    }

    const prev = snapshot.tasks.find(t => t.taskId === taskId);
    const tasks = upsertTask(snapshot.tasks, {
        taskId,
        title: titleFromMsg || prev?.title || taskId,
        taskType: taskType || prev?.taskType,
        phase: phase ?? prev?.phase ?? "waiting",
        lastMessage: msg || prev?.lastMessage || "",
        retryCount: retryBump ? (prev?.retryCount ?? 0) + 1 : prev?.retryCount,
    });

    const activeTaskId = phase && ACTIVE_PHASES.has(phase)
        ? taskId
        : snapshot.activeTaskId === taskId && phase === "executed"
            ? null
            : snapshot.activeTaskId;

    return {
        tasks: [...tasks].sort((a, b) => a.order - b.order),
        activeTaskId: activeTaskId && tasks.some(t => t.taskId === activeTaskId)
            ? activeTaskId
            : (tasks.find(t => ACTIVE_PHASES.has(t.phase))?.taskId ?? null),
        logs,
    };
}

/** 생성 완료 시 미완료 task 보정 */
export function finalizeProgressSnapshot(
    snapshot: ReportProgressSnapshot,
    plan?: { tasks?: Array<{ task_id?: string; title?: string; type?: string }> } | null,
): ReportProgressSnapshot {
    let next = hydrateProgressFromPlan(snapshot, plan);
    next = {
        ...next,
        tasks: next.tasks.map(t => (
            t.phase === "failed"
                ? t
                : { ...t, phase: "executed" as const }
        )),
        activeTaskId: null,
    };
    return next;
}

function toStepStatus(phase: TaskLifecyclePhase): ProgressStepStatus {
    if (phase === "executed") return "done";
    if (phase === "failed") return "error";
    if (ACTIVE_PHASES.has(phase)) return "active";
    return "pending";
}

/** 스냅샷 → 화면용 뷰모델 (메인 문구는 event/phase 기반, 원문은 기술 정보만) */
export function buildGenerationProgress(
    snapshot: ReportProgressSnapshot,
    options: {
        isStreaming: boolean;
        hasError: boolean;
        mode?: "generate" | "exec";
    },
): GenerationProgressView {
    const { isStreaming, hasError } = options;
    const mode = options.mode ?? "generate";
    const isExec = mode === "exec";
    const tasks = snapshot.tasks;

    if (!isStreaming && tasks.length === 0 && snapshot.logs.length === 0 && !hasError) {
        return {
            phase: "idle",
            headline: "",
            currentMessage: "",
            steps: [],
            completedCount: 0,
            totalCount: 0,
        };
    }

    const phase: GenerationProgressPhase = hasError
        ? "failed"
        : isStreaming
            ? "running"
            : "completed";

    const steps: ProgressStep[] = tasks.map(t => {
        const sub = typeSubtitle(t.taskType);
        const phaseLabel = PHASE_LABEL[t.phase];
        const userLine = toUserFacingPhaseMessage(t.phase, t.title, {
            retryCount: t.retryCount,
            rawProgressMsg: t.phase === "executing" ? t.lastMessage : undefined,
        });
        const detailParts = [
            sub,
            t.phase === "retrying" && t.retryCount > 0 ? `재시도 ${t.retryCount}` : "",
            userLine,
        ].filter(Boolean);
        return {
            id: t.taskId,
            label: t.title,
            detail: detailParts.join(" · "),
            status: toStepStatus(t.phase),
            phaseLabel,
        };
    });

    if (steps.length === 0 && (isStreaming || snapshot.logs.length > 0)) {
        steps.push({
            id: "_pipeline",
            label: isExec ? "보고서" : "보고서",
            detail: isStreaming
                ? "보고서 작성을 준비하고 있습니다"
                : "보고서 작업이 완료되었습니다",
            status: hasError ? "error" : isStreaming ? "active" : "done",
            phaseLabel: hasError ? "실패" : isStreaming ? "준비 중" : "완료",
        });
    }

    const completedCount = tasks.filter(t => t.phase === "executed").length;
    const totalCount = Math.max(tasks.length, steps.length);
    const active = tasks.find(t => t.taskId === snapshot.activeTaskId)
        ?? tasks.find(t => ACTIVE_PHASES.has(t.phase));

    let currentMessage = "";
    if (active) {
        currentMessage = toUserFacingPhaseMessage(active.phase, active.title, {
            retryCount: active.retryCount,
            rawProgressMsg: active.phase === "executing" ? active.lastMessage : undefined,
        });
    }

    if (!currentMessage) {
        if (phase === "running") {
            currentMessage = isExec
                ? "보고서를 준비하고 있습니다"
                : "보고서 작성을 준비하고 있습니다";
        } else if (phase === "completed") {
            currentMessage = isExec
                ? "보고서 미리보기가 준비되었습니다"
                : "미리보기로 확인한 뒤 등록할 수 있습니다";
        } else {
            currentMessage = active
                ? `「${active.title}」 섹션에서 문제가 발생했습니다`
                : (isExec ? "보고서를 불러오지 못했습니다" : "보고서를 완성하지 못했습니다");
        }
    }

    const headline =
        phase === "running"
            ? (isExec ? "보고서를 불러오고 있습니다" : "보고서를 작성하고 있습니다")
            : phase === "completed"
                ? (isExec ? "보고서를 불러왔습니다" : "보고서가 준비되었습니다")
                : (isExec ? "보고서를 불러오지 못했습니다" : "보고서를 완성하지 못했습니다");

    const sectionHint = active && phase === "running" && totalCount > 0
        ? `섹션 ${(tasks.findIndex(t => t.taskId === active.taskId) + 1) || completedCount + 1} / ${totalCount}`
        : "";

    return {
        phase,
        headline: sectionHint ? `${headline} · ${sectionHint}` : headline,
        currentMessage,
        steps,
        completedCount: phase === "completed" ? totalCount : completedCount,
        totalCount,
    };
}

/** @deprecated 문자열 로그만 있을 때 호환 */
export function buildGenerationProgressFromLogs(
    logs: string[],
    options: { isStreaming: boolean; hasError: boolean; mode?: "generate" | "exec" },
): GenerationProgressView {
    return buildGenerationProgress(
        { tasks: [], activeTaskId: null, logs },
        options,
    );
}
