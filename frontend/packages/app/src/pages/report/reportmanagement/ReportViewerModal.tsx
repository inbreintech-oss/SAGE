import { memo, useCallback, useEffect, useState } from "react";
import { Badge, Box, Button, Group, Modal, Text } from "@mantine/core";
import { IconPrinter, IconX } from "@tabler/icons-react";
import { ReportResultPanel } from "@/components/reportDocument";
import type { ReportGenerateResult } from "@/features/report-management";
import classes from "./reportmanagement.module.css";

export type ViewerZoomMode = "fit" | 100 | 125;

export type ReportViewerModalProps = {
    opened: boolean;
    onClose: () => void;
    result: ReportGenerateResult | null;
    isLoading?: boolean;
    error?: string | null;
    rid?: string | null;
    reportTitle?: string | null;
    emptyMessage?: string;
};

export const ReportViewerModal = memo(function ReportViewerModal({
    opened,
    onClose,
    result,
    isLoading,
    error,
    rid,
    reportTitle,
    emptyMessage,
}: ReportViewerModalProps) {
    const [zoom, setZoom] = useState<ViewerZoomMode>(125);

    useEffect(() => {
        if (opened) setZoom(125);
    }, [opened]);

    const handlePrint = useCallback(() => {
        window.print();
    }, []);

    return (
        <Modal
            opened={opened}
            onClose={onClose}
            fullScreen
            padding={0}
            withCloseButton={false}
            title={null}
            classNames={{
                content: classes.viewerShellContent,
                body: classes.viewerShellBody,
                header: classes.viewerShellHeaderHidden,
                overlay: classes.viewerShellOverlay,
            }}
            overlayProps={{ backgroundOpacity: 0.45 }}
        >
            <Box className={classes.viewerShell}>
                <Box className={classes.viewerShellToolbar}>
                    <Group gap={8} wrap="nowrap" className={classes.viewerShellToolbarMeta}>
                        <Button
                            variant="subtle"
                            size="xs"
                            color="gray"
                            leftSection={<IconX size={14} />}
                            onClick={onClose}
                            classNames={{ label: classes.viewerToolbarBtnLabel }}
                        >
                            닫기
                        </Button>
                        <Text className={classes.viewerModalTitle}>보고서 미리보기</Text>
                        {(reportTitle || rid) && (
                            <Box className={classes.viewerIdentity}>
                                {reportTitle && (
                                    <Text className={classes.viewerModalSubtitle} title={reportTitle}>
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
                    <Group gap={6} wrap="nowrap" className={classes.viewerShellToolbarActions}>
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
                            classNames={{ label: classes.viewerToolbarBtnLabel }}
                        >
                            인쇄
                        </Button>
                    </Group>
                </Box>

                <Box className={classes.viewerShellStage}>
                    <Box
                        className={classes.viewerShellPaper}
                        data-zoom={zoom}
                        data-report-print-root
                        id="report-print-preview-paper"
                    >
                        <ReportResultPanel
                            key={opened ? `viewer-${rid ?? "open"}` : "viewer-closed"}
                            result={result}
                            isLoading={isLoading}
                            error={error}
                            emptyMessage={emptyMessage}
                            scrollable={false}
                        />
                    </Box>
                </Box>
            </Box>
        </Modal>
    );
});
