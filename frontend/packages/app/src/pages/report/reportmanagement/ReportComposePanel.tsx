import { useEffect, useRef } from "react";
import {
    Alert,
    Badge,
    Box,
    Button,
    CloseButton,
    Group,
    Loader,
    Stack,
    Text,
    Textarea,
    TextInput,
} from "@mantine/core";
import {
    IconChevronsRight,
    IconEye,
    IconFileAnalytics,
    IconPlayerPlay,
    IconTool,
    IconUpload,
    IconWand,
} from "@tabler/icons-react";
import type { SageData } from "@/features/data";
import type { RecommendedToolItem, ReportLifecycle } from "@/features/report-management";
import type { ReportProgressSnapshot } from "@/features/report-management/progressSteps";
import type { ReportDraftForm } from "@/libs/stores/ReportManagementStore";
import { canSubmitGenerateDraft } from "@/libs/stores/ReportManagementStore";
import { DEFAULT_TOOL_RECOMMEND_CATEGORY } from "@/features/tool";
import { getCategoryLabel } from "@/libs/stores/toolManagement/commonCodes";
import { CopyableListItemId } from "@/components/copyableListItemId";
import { AnalysisModelEntityCard } from "./AnalysisModelEntityCard";
import { ReportGenerationProgress } from "./ReportGenerationProgress";
import dataClasses from "../../data/datamanagement.module.css";
import classes from "./reportmanagement.module.css";

export type ReportComposePanelProps = {
    hidden?: boolean;
    readonly?: boolean;
    lifecycle: ReportLifecycle;
    reportRid: string | null;
    linkedModelName: string | null;
    showExpandLeft?: boolean;
    showPreview?: boolean;
    onExpandLeft?: () => void;
    onPreview?: () => void;
    draftForm: ReportDraftForm;
    selectedData: SageData | null;
    selectedToolIds: string[];
    suggestedQueries: string[];
    recommendedTools: RecommendedToolItem[];
    toolsLoading: boolean;
    toolsError: boolean;
    streamLogs: string[];
    progressSnapshot?: ReportProgressSnapshot;
    generateError: string | null;
    execError: string | null;
    isStreaming: boolean;
    showGenerate: boolean;
    showPublish: boolean;
    showOutput: boolean;
    onDraftFieldChange: <K extends keyof ReportDraftForm>(key: K, value: ReportDraftForm[K]) => void;
    onOpenModelPicker: () => void;
    onClearModel: () => void;
    onToggleTool: (tool: RecommendedToolItem) => void;
    onRemoveTool: (toolId: string) => void;
    onClearTools: () => void;
    onGenerate: () => void;
    onPublish: () => void;
    onOutput: () => void;
};

export function ReportComposePanel({
    hidden = false,
    readonly = false,
    lifecycle,
    reportRid,
    linkedModelName,
    showExpandLeft = false,
    showPreview = false,
    onExpandLeft,
    onPreview,
    draftForm,
    selectedData,
    selectedToolIds,
    suggestedQueries,
    recommendedTools,
    toolsLoading,
    toolsError,
    streamLogs,
    progressSnapshot,
    generateError,
    execError,
    isStreaming,
    showGenerate,
    showPublish,
    showOutput,
    onDraftFieldChange,
    onOpenModelPicker,
    onClearModel,
    onToggleTool,
    onRemoveTool,
    onClearTools,
    onGenerate,
    onPublish,
    onOutput,
}: ReportComposePanelProps) {
    const progressAnchorRef = useRef<HTMLDivElement>(null);
    const wasStreamingRef = useRef(false);

    const toolMetaById = new Map(
        recommendedTools.map(t => [t.tool_id, t]),
    );

    const activeError = generateError ?? execError;
    const showActions = showPreview || showOutput || showPublish || showGenerate;
    const showProgress = isStreaming
        || streamLogs.length > 0
        || Boolean(progressSnapshot && progressSnapshot.tasks.length > 0);

    useEffect(() => {
        const started = isStreaming && !wasStreamingRef.current;
        wasStreamingRef.current = isStreaming;
        if (!started) return;

        const fitProgressInView = () => {
            const el = progressAnchorRef.current;
            if (!el) return;

            let parent: HTMLElement | null = el.parentElement;
            while (parent && parent !== document.body) {
                const { overflowY } = getComputedStyle(parent);
                if (overflowY === "auto" || overflowY === "scroll") break;
                parent = parent.parentElement;
            }

            if (!parent) {
                el.scrollIntoView({ behavior: "smooth", block: "nearest" });
                return;
            }

            const parentRect = parent.getBoundingClientRect();
            const elRect = el.getBoundingClientRect();
            const pad = 16;

            if (elRect.bottom > parentRect.bottom - pad) {
                parent.scrollTop += elRect.bottom - parentRect.bottom + pad;
            }
            if (elRect.top < parentRect.top + pad) {
                parent.scrollTop -= parentRect.top + pad - elRect.top;
            }
        };

        const frame = requestAnimationFrame(() => {
            requestAnimationFrame(fitProgressInView);
        });
        const timer = window.setTimeout(fitProgressInView, 120);
        return () => {
            cancelAnimationFrame(frame);
            window.clearTimeout(timer);
        };
    }, [isStreaming, showProgress]);

    const actionButtons = showActions ? (
        <Group justify="flex-end" gap="xs" className={classes.queryActionRow}>
            {showPreview && onPreview && (
                <Button
                    variant="light"
                    leftSection={<IconEye size={14} />}
                    onClick={onPreview}
                >
                    보고서 미리보기
                </Button>
            )}
            {showOutput && (
                <Button
                    leftSection={<IconPlayerPlay size={14} />}
                    onClick={onOutput}
                    loading={isStreaming && lifecycle === "viewing"}
                    disabled={isStreaming}
                >
                    보고서 출력
                </Button>
            )}
            {showPublish && (
                <Button
                    color="teal"
                    leftSection={<IconUpload size={14} />}
                    onClick={onPublish}
                    disabled={isStreaming}
                >
                    보고서 등록
                </Button>
            )}
            {showGenerate && (
                <Button
                    onClick={onGenerate}
                    loading={isStreaming && (lifecycle === "drafting" || lifecycle === "completed")}
                    disabled={
                        isStreaming
                        || !canSubmitGenerateDraft(selectedData?.did, draftForm)
                    }
                >
                    보고서 생성
                </Button>
            )}
        </Group>
    ) : null;

    return (
        <Box className={`${classes.panelShell} ${classes.centerPanel} ${hidden ? classes.panelHidden : ""}`}>
            <Box className={classes.panelHeader}>
                <Group gap={6}>
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
                    <IconFileAnalytics size={16} color="#1c7ed6" />
                    <Text className={classes.panelHeaderTitle}>보고서 작성</Text>
                    {readonly && (
                        <Badge size="xs" variant="light" color="gray">읽기 전용</Badge>
                    )}
                </Group>
            </Box>

            <Box className={classes.panelBody}>
                <Stack gap="md">
                    <Box>
                        <Box className={classes.fieldLabelRow}>
                            <Text className={classes.fieldLabel} mb={0}>보고서명</Text>
                            {reportRid && (
                                <CopyableListItemId
                                    label="보고서 등록 ID"
                                    value={reportRid}
                                    copiedMessage="보고서 등록 ID가 복사되었습니다."
                                />
                            )}
                        </Box>
                        <TextInput
                            size="xs"
                            placeholder="화면 표시용 보고서명"
                            value={draftForm.reportTitle}
                            onChange={e => onDraftFieldChange("reportTitle", e.currentTarget.value)}
                            readOnly={readonly}
                        />
                    </Box>

                    <Box>
                        <Text className={classes.fieldLabel}>보고서 설명</Text>
                        <Textarea
                            minRows={2}
                            size="xs"
                            placeholder="API description — 목록·상세 표기에 사용"
                            value={draftForm.description}
                            onChange={e => onDraftFieldChange("description", e.currentTarget.value)}
                            readOnly={readonly}
                        />
                    </Box>

                    <Box>
                        <Text className={classes.sectionTitle}>보고서 상세 정보</Text>
                        <Stack gap="md" mt="xs">
                            <Box>
                                <Text className={classes.fieldLabel}>분석모델</Text>
                                {selectedData ? (
                                    <AnalysisModelEntityCard
                                        model={selectedData}
                                        readonly={readonly}
                                        onChange={readonly ? undefined : onOpenModelPicker}
                                        onClear={readonly ? undefined : onClearModel}
                                    />
                                ) : readonly && linkedModelName ? (
                                    <Text size="xs" c="dimmed">{linkedModelName}</Text>
                                ) : readonly ? (
                                    <Text size="xs" c="dimmed">연결된 분석모델 정보가 없습니다.</Text>
                                ) : (
                                    <Button
                                        size="xs"
                                        variant="light"
                                        onClick={onOpenModelPicker}
                                    >
                                        분석모델 조회/선택
                                    </Button>
                                )}
                            </Box>

                            {selectedData && (
                                <>
                                    <Box>
                                        <Text className={classes.sectionTitle}>
                                            <IconWand size={12} style={{ marginRight: 4, verticalAlign: -1 }} />
                                            추천 질의문
                                        </Text>
                                        {suggestedQueries.length === 0 ? (
                                            <Text size="xs" c="dimmed">등록된 추천 질의문이 없습니다.</Text>
                                        ) : (
                                            <Box className={classes.chipRow}>
                                                {suggestedQueries.map(q => (
                                                    <Button
                                                        key={q}
                                                        size="xs"
                                                        variant={draftForm.query === q ? "filled" : "outline"}
                                                        color="blue"
                                                        className={readonly ? classes.readOnlyChip : undefined}
                                                        onClick={readonly ? undefined : () => onDraftFieldChange("query", q)}
                                                    >
                                                        {q}
                                                    </Button>
                                                ))}
                                            </Box>
                                        )}
                                    </Box>

                                    <Box>
                                        <Text className={classes.sectionTitle}>
                                            <IconTool size={12} style={{ marginRight: 4, verticalAlign: -1 }} />
                                            추천 분석 도구
                                            <Text span size="10px" c="dimmed" ml={6}>
                                                ({getCategoryLabel(DEFAULT_TOOL_RECOMMEND_CATEGORY)})
                                            </Text>
                                        </Text>
                                        {toolsLoading ? (
                                            <Loader size="xs" />
                                        ) : toolsError ? (
                                            <Text size="xs" c="red">도구 추천을 불러오지 못했습니다.</Text>
                                        ) : !recommendedTools.length && selectedToolIds.length === 0 ? (
                                            <Text size="xs" c="dimmed">추천 도구가 없습니다.</Text>
                                        ) : (
                                            <Box className={classes.chipRow}>
                                                {recommendedTools.map(tool => {
                                                    const active = selectedToolIds.includes(tool.tool_id);
                                                    return (
                                                        <Button
                                                            key={tool.tool_id}
                                                            size="xs"
                                                            variant={active ? "filled" : "light"}
                                                            color={active ? "teal" : "gray"}
                                                            className={readonly ? classes.readOnlyChip : undefined}
                                                            onClick={readonly ? undefined : () => onToggleTool(tool)}
                                                            title={tool.description}
                                                        >
                                                            {tool.title}
                                                        </Button>
                                                    );
                                                })}
                                            </Box>
                                        )}
                                    </Box>

                                    {selectedToolIds.length > 0 && (
                                        <Box>
                                            <Text className={classes.sectionTitle}>선택 도구</Text>
                                            <Group gap={6}>
                                                {selectedToolIds.map(id => (
                                                    <Badge
                                                        key={id}
                                                        variant="light"
                                                        color="teal"
                                                        className={readonly ? classes.readOnlyChip : undefined}
                                                        rightSection={
                                                            !readonly ? (
                                                                <CloseButton
                                                                    size="xs"
                                                                    aria-label="도구 제거"
                                                                    onClick={() => onRemoveTool(id)}
                                                                />
                                                            ) : undefined
                                                        }
                                                    >
                                                        {toolMetaById.get(id)?.title ?? id}
                                                    </Badge>
                                                ))}
                                                {!readonly && (
                                                    <Button size="compact-xs" variant="subtle" color="gray" onClick={onClearTools}>
                                                        모두 제거
                                                    </Button>
                                                )}
                                            </Group>
                                        </Box>
                                    )}

                                    <Box>
                                        <Text className={classes.sectionTitle}>자연어 질의</Text>
                                        <Textarea
                                            className={`${classes.queryTextarea} ${readonly ? classes.readOnlyTextarea : ""}`.trim()}
                                            minRows={5}
                                            autosize={false}
                                            placeholder="어떤 분석을 수행할까요?"
                                            value={draftForm.query}
                                            onChange={e => onDraftFieldChange("query", e.currentTarget.value)}
                                            readOnly={readonly}
                                        />
                                        {actionButtons}
                                    </Box>
                                </>
                            )}

                            {!selectedData && actionButtons}
                        </Stack>
                    </Box>

                    {showProgress && (
                        <Box ref={progressAnchorRef}>
                            <ReportGenerationProgress
                                snapshot={progressSnapshot}
                                streamLogs={streamLogs}
                                isStreaming={isStreaming}
                                hasError={Boolean(generateError)}
                            />
                        </Box>
                    )}

                    {activeError && (
                        <Alert color="red" variant="light" title="오류">
                            {activeError}
                        </Alert>
                    )}
                </Stack>
            </Box>
        </Box>
    );
}
