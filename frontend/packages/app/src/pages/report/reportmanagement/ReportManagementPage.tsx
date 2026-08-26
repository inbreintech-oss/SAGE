/**

 * ReportManagementPage — 보고서 관리 (목록 + 작성 워크스페이스, 뷰어 Print Preview Shell)

 * lifecycle: drafting → completed → published | viewing

 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Box } from "@mantine/core";

import { useShallow } from "zustand/react/shallow";

import { DefaultAppPageLayout } from "@/layouts/appPage";

import { useDataList, selectCompletedDataList } from "@/features/data";

import { DEFAULT_TOOL_RECOMMEND_CATEGORY } from "@/features/tool";

import {

    canReopenPreview,

    canShowGenerateButton,

    canShowOutputButton,

    canShowPublishButton,

    derivePanelLayout,

    isCenterReadonly,

    usePublishedReportList,

    usePublishReport,

    useRecommendedTools,

    type ReportListItem,

} from "@/features/report-management";

import { generateReportWithLogs, execReportWithLogs } from "@/features/report-management/streamHelpers";

import {

    canSubmitGenerateDraft,

    resolveGenerateDescription,

    useReportManagementStore,

} from "@/libs/stores/ReportManagementStore";

import { FetchAPIError } from "@/features/Utils";

import { useNotifications } from "@/hooks";

import { AnalysisModelPickerModal } from "./AnalysisModelPickerModal";

import { ReportComposePanel } from "./ReportComposePanel";

import { ReportPublishedListPanel } from "./ReportPublishedListPanel";

import { ReportViewerModal } from "./ReportViewerModal";

import classes from "./reportmanagement.module.css";



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



export default function ReportManagementPage() {

    const abortRef = useRef<AbortController | null>(null);

    const [pickerOpen, setPickerOpen] = useState(false);

    const [viewerOpen, setViewerOpen] = useState(false);

    const [leftManualCollapsed, setLeftManualCollapsed] = useState(false);



    const { showSuccess, showError } = useNotifications();



    const store = useReportManagementStore(useShallow(s => ({

        lifecycle: s.lifecycle,

        selectedReport: s.selectedReport,

        selectedData: s.selectedData,

        selectedToolIds: s.selectedToolIds,

        draftForm: s.draftForm,

        reportResult: s.reportResult,

        currentRid: s.currentRid,

        streamLogs: s.streamLogs,
        progressSnapshot: s.progressSnapshot,
        generateError: s.generateError,
        execError: s.execError,
        isStreaming: s.isStreaming,
        startNewReport: s.startNewReport,
        selectPublishedReport: s.selectPublishedReport,
        setSelectedData: s.setSelectedData,
        clearSelectedData: s.clearSelectedData,
        toggleTool: s.toggleTool,
        removeTool: s.removeTool,
        clearTools: s.clearTools,
        setDraftField: s.setDraftField,
        appendStreamLog: s.appendStreamLog,
        clearStreamLogs: s.clearStreamLogs,
        resetProgress: s.resetProgress,
        applyStreamEvent: s.applyStreamEvent,
        setIsStreaming: s.setIsStreaming,
        setGenerateError: s.setGenerateError,
        setExecError: s.setExecError,

        onGenerateSuccess: s.onGenerateSuccess,

        onPublishSuccess: s.onPublishSuccess,

        onExecSuccess: s.onExecSuccess,

    })));



    const {

        lifecycle,

        selectedReport,

        selectedData,

        selectedToolIds,

        draftForm,

        reportResult,

        currentRid,

        streamLogs,

        progressSnapshot,

        generateError,

        execError,

        isStreaming,

    } = store;



    const { data: publishedList, isLoading: listLoading, isError: listError, refetch: refetchList } = usePublishedReportList();

    const {
        data: allDataList,
        isLoading: modelsLoading,
        isError: modelsError,
        refetch: refetchModels,
    } = useDataList();



    const handleOpenModelPicker = useCallback(() => {

        setPickerOpen(true);

        void refetchModels();

    }, [refetchModels]);



    const pickerModels = useMemo(
        () => selectCompletedDataList(allDataList),
        [allDataList],
    );

    const modelsForNames = allDataList ?? [];



    const suggestedQueries = useMemo(

        () => selectedData?.suggested_queries ?? [],

        [selectedData],

    );



    const linkedModelName = useMemo(() => {

        if (selectedData?.name) return selectedData.name;

        const did = selectedReport?.did;

        if (!did) return null;

        return modelsForNames.find(m => m.did === did)?.name ?? null;

    }, [selectedData, selectedReport, modelsForNames]);



    const reportRid = currentRid ?? reportResult?.rid ?? null;

    const viewerReportTitle = useMemo(() => {
        const draftTitle = draftForm.reportTitle.trim() || draftForm.description.trim();
        const listTitle = selectedReport
            ? (selectedReport.description?.trim() || selectedReport.title?.trim() || "")
            : "";
        if (lifecycle === "viewing") {
            return listTitle || draftTitle || null;
        }
        return draftTitle || listTitle || null;
    }, [draftForm.reportTitle, draftForm.description, selectedReport, lifecycle]);

    const {

        data: recommendedTools,

        isLoading: toolsLoading,

        isError: toolsError,

    } = useRecommendedTools(selectedData?.did, DEFAULT_TOOL_RECOMMEND_CATEGORY);



    const publishMutation = usePublishReport();



    const layout = derivePanelLayout(lifecycle);

    const leftVisible = layout.leftOpen && !leftManualCollapsed;

    const centerVisible = layout.centerOpen;

    const centerReadonly = isCenterReadonly(lifecycle);

    const canReopenViewer = canReopenPreview(lifecycle, Boolean(reportResult?.report));



    const openViewer = useCallback(() => setViewerOpen(true), []);

    const closeViewer = useCallback(() => setViewerOpen(false), []);



    useEffect(() => {

        if (lifecycle === "completed") {

            setViewerOpen(true);

            return;

        }

        if (lifecycle === "published" || lifecycle === "drafting") {

            setViewerOpen(false);

        }

    }, [lifecycle]);



    useEffect(() => {

        if (!layout.leftOpen) setLeftManualCollapsed(false);

    }, [layout.leftOpen]);



    const cancelStream = useCallback(() => {

        abortRef.current?.abort();

        abortRef.current = null;

    }, []);



    const handleStartNew = useCallback(() => {

        cancelStream();

        setViewerOpen(false);

        setLeftManualCollapsed(false);

        store.startNewReport();

    }, [cancelStream, store]);



    const handleSelectPublished = useCallback((item: ReportListItem) => {

        cancelStream();

        setViewerOpen(false);

        setLeftManualCollapsed(false);

        const model = item.did
            ? modelsForNames.find(m => m.did === item.did) ?? null
            : null;

        store.selectPublishedReport(item, model);

    }, [cancelStream, store, modelsForNames]);



    const handleGenerate = useCallback(async () => {

        if (!canSubmitGenerateDraft(selectedData?.did, draftForm)) return;



        cancelStream();

        const controller = new AbortController();

        abortRef.current = controller;



        store.resetProgress();

        store.setGenerateError(null);

        store.setIsStreaming(true);



        const apiDescription = resolveGenerateDescription(draftForm);



        try {

            const result = await generateReportWithLogs(

                {

                    did: selectedData!.did,

                    query: draftForm.query.trim(),

                    tools: selectedToolIds,

                    description: apiDescription,

                },

                {

                    onEvent: event => store.applyStreamEvent(event),

                },

                controller.signal,

            );

            store.onGenerateSuccess(result);

            openViewer();

            showSuccess("보고서가 생성되었습니다.");

        } catch (error) {

            if (controller.signal.aborted) return;

            const msg = resolveErrorMessage(error, "보고서 생성에 실패했습니다.");

            store.setGenerateError(msg);

            store.setIsStreaming(false);

            showError(msg);

        }

    }, [selectedData, draftForm, selectedToolIds, cancelStream, store, showSuccess, showError, openViewer]);



    const handlePublish = useCallback(async () => {

        const rid = currentRid ?? reportResult?.rid;

        if (!rid) {

            showError("등록할 보고서 RID가 없습니다.");

            return;

        }



        try {

            const published = await publishMutation.mutateAsync({ rid });

            store.onPublishSuccess(published);

            setViewerOpen(false);

            showSuccess("보고서가 등록(배포)되었습니다.");

            void refetchList();

        } catch (error) {

            const msg = resolveErrorMessage(error, "보고서 등록에 실패했습니다.");

            showError(msg);

        }

    }, [currentRid, reportResult, publishMutation, store, showSuccess, showError, refetchList]);



    const handleOutput = useCallback(async () => {

        const rid = currentRid ?? selectedReport?.rid;

        if (!rid) {

            showError("실행할 보고서 RID가 없습니다.");

            return;

        }



        cancelStream();

        const controller = new AbortController();

        abortRef.current = controller;



        store.resetProgress();

        store.setExecError(null);

        store.setIsStreaming(true);



        try {

            const result = await execReportWithLogs(

                { rid },

                {

                    onEvent: event => store.applyStreamEvent(event),

                },

                controller.signal,

            );

            store.onExecSuccess(result);

            openViewer();

            showSuccess("보고서 출력이 완료되었습니다.");

        } catch (error) {

            if (controller.signal.aborted) return;

            const msg = resolveErrorMessage(error, "보고서 출력에 실패했습니다.");

            store.setExecError(msg);

            store.setIsStreaming(false);

            showError(msg);

        }

    }, [currentRid, selectedReport, cancelStream, store, showSuccess, showError, openViewer]);



    const viewerLoading = isStreaming && viewerOpen && lifecycle === "completed";

    const viewerError = viewerOpen

        ? (lifecycle === "viewing" ? execError : generateError)

        : null;



    return (

        <DefaultAppPageLayout title="보고서">

            <Box className={`${classes.workspace} ${leftManualCollapsed ? classes.workspaceCollapsed : ""}`}>

                <ReportPublishedListPanel

                    items={publishedList ?? []}

                    models={modelsForNames}

                    isLoading={listLoading}

                    isError={listError}

                    selectedRid={selectedReport?.rid ?? currentRid}

                    hidden={!leftVisible}

                    onSelect={handleSelectPublished}

                    onCreateNew={handleStartNew}

                    onReload={() => { void refetchList(); }}

                    onCollapse={layout.leftOpen ? () => setLeftManualCollapsed(true) : undefined}

                />



                <ReportComposePanel

                    hidden={!centerVisible}

                    readonly={centerReadonly}

                    lifecycle={lifecycle}

                    reportRid={reportRid}

                    linkedModelName={linkedModelName}

                    showExpandLeft={layout.leftOpen && leftManualCollapsed}

                    showPreview={canReopenViewer && !viewerOpen}

                    onExpandLeft={() => setLeftManualCollapsed(false)}

                    onPreview={openViewer}

                    draftForm={draftForm}

                    selectedData={selectedData}

                    selectedToolIds={selectedToolIds}

                    suggestedQueries={suggestedQueries}

                    recommendedTools={recommendedTools ?? []}

                    toolsLoading={toolsLoading}

                    toolsError={toolsError}

                    streamLogs={streamLogs}

                    progressSnapshot={progressSnapshot}

                    generateError={generateError}

                    execError={execError}

                    isStreaming={isStreaming}

                    showGenerate={canShowGenerateButton(lifecycle)}

                    showPublish={canShowPublishButton(lifecycle)}

                    showOutput={canShowOutputButton(lifecycle)}

                    onDraftFieldChange={store.setDraftField}

                    onOpenModelPicker={handleOpenModelPicker}

                    onClearModel={store.clearSelectedData}

                    onToggleTool={store.toggleTool}

                    onRemoveTool={store.removeTool}

                    onClearTools={store.clearTools}

                    onGenerate={() => { void handleGenerate(); }}

                    onPublish={() => { void handlePublish(); }}

                    onOutput={() => { void handleOutput(); }}

                />

            </Box>



            <ReportViewerModal

                opened={viewerOpen}

                onClose={closeViewer}

                result={reportResult}

                isLoading={viewerLoading}

                error={viewerError}

                rid={currentRid ?? reportResult?.rid}

                reportTitle={viewerReportTitle}

                emptyMessage={

                    lifecycle === "viewing"

                        ? "보고서 출력을 실행하면 결과가 표시됩니다."

                        : "보고서를 생성하면 이 영역에 결과가 표시됩니다."

                }

            />



            <AnalysisModelPickerModal

                opened={pickerOpen}

                onClose={() => setPickerOpen(false)}

                models={pickerModels}

                isLoading={modelsLoading}

                isError={modelsError}

                selectedDid={selectedData?.did ?? null}

                onSelect={model => {

                    store.setSelectedData(model);

                    setPickerOpen(false);

                }}

                onReload={() => { void refetchModels(); }}

            />

        </DefaultAppPageLayout>

    );

}


