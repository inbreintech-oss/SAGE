import { memo, useCallback, useState, type RefObject } from "react";
import { Badge, Box, Button, Group, Text } from "@mantine/core";
import { IconChevronsRight, IconDownload, IconPrinter } from "@tabler/icons-react";
import { ReportResultPanel } from "@/components/reportDocument";
import type { ReportGenerateResult } from "@/features/report-management";
import type { ReportProgressSnapshot } from "@/features/report-management/progressSteps";
import { ReportGenerationProgress } from "../reportmanagement/ReportGenerationProgress";
import dataClasses from "../../data/datamanagement.module.css";
import classes from "./reportlist.module.css";

export type ViewerZoomMode = "fit" | 100 | 125;

export type ReportBrowseViewerPanelProps = {
    result: ReportGenerateResult | null;
    isLoading?: boolean;
    error?: string | null;
    rid?: string | null;
    reportTitle?: string | null;
    hasSelection?: boolean;
    streamLogs?: string[];
    progressSnapshot?: ReportProgressSnapshot;
    pdfTargetRef?: RefObject<HTMLDivElement | null>;
    onDownload?: () => void;
    downloadDisabled?: boolean;
    showExpandLeft?: boolean;
    onExpandLeft?: () => void;
};

export const ReportBrowseViewerPanel = memo(function ReportBrowseViewerPanel({
    result,
    isLoading,
    error,
    rid,
    reportTitle,
    hasSelection = false,
    streamLogs = [],
    progressSnapshot,
    pdfTargetRef,
    onDownload,
    downloadDisabled = true,
    showExpandLeft = false,
    onExpandLeft,
}: ReportBrowseViewerPanelProps) {
    const [zoom, setZoom] = useState<ViewerZoomMode>(125);

    const handlePrint = useCallback(() => {
        window.print();
    }, []);

    const showToolbar = hasSelection;
    const showProgressOverlay = hasSelection && (
        Boolean(isLoading)
        || (Boolean(error) && ((progressSnapshot?.tasks.length ?? 0) > 0 || streamLogs.length > 0) && !result)
    );

    return (
        <Box className={classes.viewerPanel}>
            <Box className={classes.viewerPanelToolbar}>
                <Group gap={8} wrap="nowrap" className={classes.viewerPanelToolbarMeta}>
                    {showExpandLeft && onExpandLeft && (
                        <button
                            type="button"
                            className={dataClasses.expandBtn}
                            title="목록 보이기"
                            onClick={onExpandLeft}
                        >
                            <IconChevronsRight size={14} />
                        </button>
                    )}
                    <Text className={classes.viewerPanelTitle}>보고서 미리보기</Text>
                    {(reportTitle || rid) && (
                        <Box className={classes.viewerIdentity}>
                            {reportTitle && (
                                <Text className={classes.viewerPanelSubtitle} title={reportTitle}>
                                    {reportTitle}
                                </Text>
                            )}
                            {rid && (
                                <Badge
                                    size="xs"
                                    variant="outline"
                                    color="gray"
                                    className={classes.viewerRidBadge}
                                    title={`RID: ${rid}`}
                                >
                                    RID: {rid}
                                </Badge>
                            )}
                        </Box>
                    )}
                </Group>
                {showToolbar && (
                    <Group gap={6} wrap="nowrap" className={classes.viewerPanelToolbarActions}>
                        <Button
                            variant={zoom === "fit" ? "light" : "subtle"}
                            size="xs"
                            color="gray"
                            onClick={() => setZoom("fit")}
                            classNames={{ label: classes.viewerToolbarBtnLabel }}
                        >
                            맞춤
                        </Button>
                        <Button
                            variant={zoom === 100 ? "light" : "subtle"}
                            size="xs"
                            color="gray"
                            onClick={() => setZoom(100)}
                            classNames={{ label: classes.viewerToolbarBtnLabel }}
                        >
                            100%
                        </Button>
                        <Button
                            variant={zoom === 125 ? "light" : "subtle"}
                            size="xs"
                            color="gray"
                            onClick={() => setZoom(125)}
                            classNames={{ label: classes.viewerToolbarBtnLabel }}
                        >
                            125%
                        </Button>
                        <Button
                            variant="light"
                            size="xs"
                            color="blue"
                            leftSection={<IconPrinter size={14} />}
                            onClick={handlePrint}
                            disabled={isLoading || !!error || !result}
                            classNames={{ label: classes.viewerToolbarBtnLabel }}
                        >
                            인쇄
                        </Button>
                        <Button
                            variant="light"
                            size="xs"
                            color="blue"
                            leftSection={<IconDownload size={14} />}
                            onClick={onDownload}
                            disabled={downloadDisabled}
                            classNames={{ label: classes.viewerToolbarBtnLabel }}
                        >
                            다운로드
                        </Button>
                    </Group>
                )}
            </Box>

            <Box className={classes.viewerPanelStage}>
                {!hasSelection ? (
                    <Box className={classes.viewerPanelEmpty}>
                        <Text size="sm" c="dimmed">좌측 목록에서 보고서를 선택하세요.</Text>
                    </Box>
                ) : showProgressOverlay ? (
                    <Box className={classes.viewerProgressOverlay}>
                        <ReportGenerationProgress
                            snapshot={progressSnapshot}
                            streamLogs={streamLogs}
                            isStreaming={Boolean(isLoading)}
                            hasError={Boolean(error)}
                            mode="exec"
                            hideSectionTitle
                        />
                        {error && (
                            <Text size="sm" c="red" mt="sm">{error}</Text>
                        )}
                    </Box>
                ) : (
                    <Box
                        ref={pdfTargetRef}
                        className={classes.viewerPanelPaper}
                        data-zoom={zoom}
                        data-report-print-root
                        id="report-list-preview-paper"
                    >
                        <ReportResultPanel
                            key={rid ?? "no-rid"}
                            result={result}
                            isLoading={false}
                            error={error}
                            emptyMessage="보고서 출력 결과가 표시됩니다."
                            scrollable={false}
                        />
                    </Box>
                )}
            </Box>
        </Box>
    );
});
