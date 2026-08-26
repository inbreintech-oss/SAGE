/**
 * ReportListBrowsePage — 보고서 목록
 * 좌: 배포 보고서 목록 / 우: 패널 내 미리보기 (줌·인쇄·다운로드)
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Box } from "@mantine/core";
import { usePDF } from "react-to-pdf";
import { DefaultAppPageLayout } from "@/layouts/appPage";
import { useCompletedDataList } from "@/features/data";
import {
    usePublishedReportList,
    type ReportGenerateResult,
    type ReportListItem,
} from "@/features/report-management";
import {
    applyProgressEvent,
    createEmptyProgressSnapshot,
    finalizeProgressSnapshot,
    type ReportProgressSnapshot,
} from "@/features/report-management/progressSteps";
import { execReportWithLogs } from "@/features/report-management/streamHelpers";
import { FetchAPIError } from "@/features/Utils";
import { useNotifications } from "@/hooks";
import { ReportBrowseListPanel } from "./ReportBrowseListPanel";
import { ReportBrowseViewerPanel } from "./ReportBrowseViewerPanel";
import classes from "./reportlist.module.css";

function resolveErrorMessage(error: unknown, fallback: string): string {
    if (error instanceof FetchAPIError) {
        if (typeof error.data === "object" && error.data && "error" in error.data) {
            return String((error.data as { error?: unknown }).error ?? fallback);
        }
        return fallback;
    }
    if (error instanceof Error) return error.message;
    return fallback;
}

function resolveReportTitle(item: ReportListItem | null): string | null {
    if (!item) return null;
    return item.description?.trim() || item.title?.trim() || null;
}

export default function ReportListBrowsePage() {
    const abortRef = useRef<AbortController | null>(null);
    const [selectedReport, setSelectedReport] = useState<ReportListItem | null>(null);
    const [reportResult, setReportResult] = useState<ReportGenerateResult | null>(null);
    const [isExecLoading, setIsExecLoading] = useState(false);
    const [execError, setExecError] = useState<string | null>(null);
    const [progressSnapshot, setProgressSnapshot] = useState<ReportProgressSnapshot>(
        createEmptyProgressSnapshot(),
    );
    const [leftCollapsed, setLeftCollapsed] = useState(false);

    const { showError } = useNotifications();
    const { data: publishedList, isLoading: listLoading, isError: listError, refetch: refetchList } = usePublishedReportList();
    const { data: completedModels } = useCompletedDataList();

    const modelsForNames = useMemo(() => completedModels ?? [], [completedModels]);

    const { toPDF, targetRef } = usePDF();

    const cancelExec = useCallback(() => {
        abortRef.current?.abort();
        abortRef.current = null;
    }, []);

    const runExec = useCallback(async (item: ReportListItem) => {
        cancelExec();
        setSelectedReport(item);
        setReportResult(null);
        setExecError(null);
        setProgressSnapshot(createEmptyProgressSnapshot());
        setIsExecLoading(true);

        const controller = new AbortController();
        abortRef.current = controller;

        try {
            const result = await execReportWithLogs(
                { rid: item.rid },
                {
                    onEvent: event => {
                        if (controller.signal.aborted) return;
                        setProgressSnapshot(prev => applyProgressEvent(prev, event as Record<string, unknown>));
                    },
                },
                controller.signal,
            );
            if (!controller.signal.aborted) {
                setReportResult(result);
                setProgressSnapshot(prev => finalizeProgressSnapshot(prev, result.plan));
            }
        } catch (error) {
            if (controller.signal.aborted) return;
            const msg = resolveErrorMessage(error, "보고서 출력에 실패했습니다.");
            setExecError(msg);
            showError(msg);
        } finally {
            if (!controller.signal.aborted) {
                setIsExecLoading(false);
            }
        }
    }, [cancelExec, showError]);

    const handleSelect = useCallback((item: ReportListItem) => {
        if (item.rid === selectedReport?.rid && isExecLoading) return;
        void runExec(item);
    }, [selectedReport?.rid, isExecLoading, runExec]);

    const handleDownload = useCallback(() => {
        if (!reportResult || isExecLoading) return;
        const filename = resolveReportTitle(selectedReport) ?? selectedReport?.rid ?? "report-export";
        void toPDF({ filename: `${filename}.pdf` });
    }, [reportResult, isExecLoading, selectedReport, toPDF]);

    useEffect(() => () => {
        cancelExec();
    }, [cancelExec]);

    const downloadDisabled = !selectedReport || isExecLoading || !!execError || !reportResult;

    return (
        <DefaultAppPageLayout title="보고서 목록">
            <Box className={`${classes.workspace} ${leftCollapsed ? classes.workspaceCollapsed : ""}`}>
                <ReportBrowseListPanel
                    items={publishedList ?? []}
                    models={modelsForNames}
                    isLoading={listLoading}
                    isError={listError}
                    selectedRid={selectedReport?.rid ?? null}
                    collapsed={leftCollapsed}
                    onSelect={handleSelect}
                    onReload={() => { void refetchList(); }}
                    onCollapse={() => setLeftCollapsed(true)}
                />

                <ReportBrowseViewerPanel
                    result={reportResult}
                    isLoading={isExecLoading}
                    error={execError}
                    rid={selectedReport?.rid ?? null}
                    reportTitle={resolveReportTitle(selectedReport)}
                    hasSelection={selectedReport !== null}
                    progressSnapshot={progressSnapshot}
                    streamLogs={progressSnapshot.logs}
                    pdfTargetRef={targetRef}
                    onDownload={handleDownload}
                    downloadDisabled={downloadDisabled}
                    showExpandLeft={leftCollapsed}
                    onExpandLeft={() => setLeftCollapsed(false)}
                />
            </Box>
        </DefaultAppPageLayout>
    );
}
