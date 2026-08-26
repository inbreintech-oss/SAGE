import { useEffect, useMemo, useRef, useState } from "react";
import {
    Badge,
    Box,
    Collapse,
    Group,
    Progress,
    ScrollArea,
    Stack,
    Text,
    UnstyledButton,
} from "@mantine/core";
import {
    IconCheck,
    IconChevronDown,
    IconCircle,
    IconLoader2,
    IconX,
} from "@tabler/icons-react";
import {
    buildGenerationProgress,
    createEmptyProgressSnapshot,
    type ProgressStepStatus,
    type ReportProgressSnapshot,
} from "@/features/report-management/progressSteps";
import { DARK_CONSOLE_SCROLL_PROPS, DARK_CONSOLE_SCROLL_STYLES } from "@/styles/darkConsoleScroll";
import classes from "./reportmanagement.module.css";

export type ReportGenerationProgressProps = {
    snapshot?: ReportProgressSnapshot;
    /** @deprecated snapshot.logs 우선 — 하위 호환 */
    streamLogs?: string[];
    isStreaming: boolean;
    hasError: boolean;
    mode?: "generate" | "exec";
    title?: string;
    hideSectionTitle?: boolean;
};

function StepIcon({ status }: { status: ProgressStepStatus }) {
    if (status === "done") {
        return <IconCheck size={14} className={classes.progressStepIconDone} />;
    }
    if (status === "active") {
        return <IconLoader2 size={14} className={classes.progressStepIconActive} />;
    }
    if (status === "error") {
        return <IconX size={14} className={classes.progressStepIconError} />;
    }
    return <IconCircle size={12} className={classes.progressStepIconPending} />;
}

function phaseBadge(phase: "running" | "completed" | "failed", mode: "generate" | "exec") {
    if (phase === "running") {
        return (
            <Badge size="sm" variant="light" color="blue">
                {mode === "exec" ? "불러오는 중" : "생성 중"}
            </Badge>
        );
    }
    if (phase === "completed") {
        return <Badge size="sm" variant="light" color="teal">완료</Badge>;
    }
    return <Badge size="sm" variant="light" color="red">실패</Badge>;
}

export function ReportGenerationProgress({
    snapshot,
    streamLogs,
    isStreaming,
    hasError,
    mode = "generate",
    title,
    hideSectionTitle = false,
}: ReportGenerationProgressProps) {
    const [techOpen, setTechOpen] = useState(false);
    const consoleViewportRef = useRef<HTMLDivElement>(null);

    const resolvedSnapshot = useMemo<ReportProgressSnapshot>(() => {
        if (snapshot) return snapshot;
        return {
            ...createEmptyProgressSnapshot(),
            logs: streamLogs ?? [],
        };
    }, [snapshot, streamLogs]);

    const view = useMemo(
        () => buildGenerationProgress(resolvedSnapshot, { isStreaming, hasError, mode }),
        [resolvedSnapshot, isStreaming, hasError, mode],
    );

    const techLogs = resolvedSnapshot.logs;
    const sectionTitle = title ?? (mode === "exec" ? "불러오기 진행" : "작성 진행");

    useEffect(() => {
        if (!techOpen) return;
        const el = consoleViewportRef.current;
        if (el) el.scrollTop = el.scrollHeight;
    }, [techLogs, techOpen]);

    if (view.phase === "idle") return null;

    const progressValue = view.totalCount > 0
        ? (view.completedCount / view.totalCount) * 100
            + (view.phase === "running" ? (1 / view.totalCount) * 40 : 0)
        : (view.phase === "running" ? 15 : 100);

    return (
        <Box>
            {!hideSectionTitle && (
                <Text className={classes.sectionTitle}>{sectionTitle}</Text>
            )}
            <Box className={classes.progressPanel}>
                <Group justify="space-between" align="flex-start" wrap="nowrap" mb={10}>
                    <Stack gap={2} style={{ minWidth: 0 }}>
                        <Text className={classes.progressHeadline}>{view.headline}</Text>
                        <Text className={classes.progressCurrent}>{view.currentMessage}</Text>
                    </Stack>
                    {phaseBadge(view.phase, mode)}
                </Group>

                <Progress
                    value={Math.min(100, progressValue)}
                    size="sm"
                    radius="sm"
                    color={view.phase === "failed" ? "red" : view.phase === "completed" ? "teal" : "blue"}
                    animated={view.phase === "running"}
                    mb="sm"
                />

                <Text size="xs" c="dimmed" mb={8}>
                    {view.totalCount > 0
                        ? `${view.completedCount} / ${view.totalCount} 섹션`
                        : "보고서 준비 중"}
                    {view.phase === "running" ? " · 잠시만 기다려 주세요" : ""}
                </Text>

                <Stack gap={6} mb={techOpen || techLogs.length > 0 ? 10 : 0}>
                    {view.steps.map(step => (
                        <Group
                            key={step.id}
                            gap={8}
                            wrap="nowrap"
                            className={`${classes.progressStepRow} ${
                                step.status === "active" ? classes.progressStepRowActive : ""
                            }`}
                        >
                            <Box className={classes.progressStepIconWrap}>
                                <StepIcon status={step.status} />
                            </Box>
                            <Box style={{ minWidth: 0, flex: 1 }}>
                                <Group gap={6} wrap="nowrap" justify="space-between">
                                    <Text
                                        size="sm"
                                        fw={step.status === "active" || step.status === "error" ? 600 : 500}
                                        c={
                                            step.status === "pending"
                                                ? "dimmed"
                                                : step.status === "error"
                                                    ? "red"
                                                    : undefined
                                        }
                                        lineClamp={1}
                                    >
                                        {step.label}
                                    </Text>
                                    <Badge
                                        size="xs"
                                        variant="light"
                                        color={
                                            step.status === "done"
                                                ? "teal"
                                                : step.status === "error"
                                                    ? "red"
                                                    : step.status === "active"
                                                        ? "blue"
                                                        : "gray"
                                        }
                                    >
                                        {step.phaseLabel}
                                    </Badge>
                                </Group>
                                <Text size="xs" c="dimmed" lineClamp={2}>
                                    {step.detail}
                                </Text>
                            </Box>
                        </Group>
                    ))}
                </Stack>

                {techLogs.length > 0 && (
                    <Box>
                        <UnstyledButton
                            className={classes.progressTechToggle}
                            onClick={() => setTechOpen(v => !v)}
                            aria-expanded={techOpen}
                        >
                            <Text size="xs" c="dimmed">기술 정보</Text>
                            <IconChevronDown
                                size={14}
                                className={classes.schemaChevron}
                                data-expanded={techOpen || undefined}
                            />
                        </UnstyledButton>
                        <Collapse in={techOpen}>
                            <Box className={classes.consoleCard} mt={6}>
                                <ScrollArea
                                    className={classes.consoleScrollArea}
                                    h={140}
                                    viewportRef={consoleViewportRef}
                                    styles={DARK_CONSOLE_SCROLL_STYLES}
                                    {...DARK_CONSOLE_SCROLL_PROPS}
                                >
                                    {techLogs.map((line, i) => (
                                        <Text
                                            key={`${i}-${line.slice(0, 24)}`}
                                            className={classes.consoleLine}
                                        >
                                            {line}
                                        </Text>
                                    ))}
                                </ScrollArea>
                            </Box>
                        </Collapse>
                    </Box>
                )}
            </Box>
        </Box>
    );
}
