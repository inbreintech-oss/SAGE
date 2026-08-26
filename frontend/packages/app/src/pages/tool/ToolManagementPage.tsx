/**
 * ToolManagementPage — 도구(API) 관리 v1.7.3 Split Console & Dynamic Lifecycle
 */
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
    Box,
    Button,
    Group,
    Loader,
    ScrollArea,
    Select,
    Stack,
    Table,
    Text,
    Textarea,
    TextInput,
} from "@mantine/core";
import {
    IconArrowBackUp,
    IconBolt,
    IconBraces,
    IconChevronsLeft,
    IconChevronsRight,
    IconDeviceFloppy,
    IconPencil,
    IconPlayerPlay,
    IconPointer,
    IconRefresh,
    IconSettings,
    IconSquareRoot,
    IconTerminal,
    IconTrash,
    IconWand,
} from "@tabler/icons-react";
import katex from "katex";
import { DefaultAppPageLayout } from "@/layouts/appPage";
import {
    toolDelete,
    toolGenerate,
    toolAssetize,
    toolInfo,
    toolListTokenTools,
    toolExec,
    toolUpdate,
    secretList,
    useTool,
    type ToolGenerateResponse,
    type SecretKeyItem,
    type ToolListResponse,
} from "@/features/tool";
import {
    normalizeToolItem,
    mergeToolListItemFromCache,
    resolveExecPreview,
    buildGeneratePayload,
    buildUpdateApiPayload,
    buildAssetizeApiPayload,
    buildAssetPath,
    buildToolExecTools,
    mapToolSSEEventToTraceLine,
    normalizeToolExecResult,
    useToolState,
    TOKEN_TOOL_FIELD_LABEL,
    TOKEN_TOOL_EMPTY_HINT,
    buildTokenExecErrorMessage,
    isLikelyTokenAuthError,
    resolveExecQueryText,
    filterToolsForManagementList,
} from "@/features/tool-management";
import ToolListPanel from "@/pages/tool/ToolListPanel";
import {
    buildGenerateResultPreview,
    buildToolSyncResultPreview,
    buildExecRequestPreview,
    buildExecResponsePreview,
    formatTraceTimestamp,
} from "@/libs/stores/toolManagement/consolePreview";
import { FetchAPIError } from "@/features/Utils";
import { parseToolApiError, parseToolApiErrorForToast } from "@/features/tool/parseToolApiError";
import { useCommonModals, useNotifications } from "@/hooks";
import { DARK_CONSOLE_SCROLL_PROPS, DARK_CONSOLE_SCROLL_STYLES } from "@/styles/darkConsoleScroll";
import {
    LIST_LOAD_ERROR_MESSAGE,
    ALREADY_SAVED_MESSAGE,
    SCHEMA_ALREADY_EXISTS_MESSAGE,
    DEFAULT_CATEGORY_CODE,
    populateCategoryOptions,
    VISUAL_EXEC_GUIDE_DESC,
    VISUAL_SELECT_GUIDE_DESC,
} from "@/libs/stores/toolManagement/constants";
import { parseExecVisualResult } from "@/features/tool-management/parseExecVisualResult";
import type { RequiredFormField, ToolFormDraft, ToolListItem } from "@/libs/stores/toolManagement/types";
import { updateToolInList } from "@/libs/stores/toolManagement/useToolManagementSelectors";
import { useToolManagementStore } from "@/libs/stores/ToolManagementStore";
import { sortToolListItems } from "@/libs/sortListItems";
import { CopyableListItemId } from "@/components/copyableListItemId";
import classes from "./toolmanagement.module.css";

function buildFallbackExecPlaceholder(title: string): string {
    return `${title} 도구를 활용한 자연어 미리보기 정합성 검증을 시동해줘.`;
}

function buildGeneratedListItem(
    toolId: string,
    draft: ToolFormDraft,
    code: string,
    execRecommendation?: string,
): ToolListItem {
    const recommendation = execRecommendation?.trim()
        || buildFallbackExecPlaceholder(draft.title.trim() || "신규");

    return {
        tool_id: toolId,
        title: draft.title.trim(),
        description: draft.description.trim(),
        category: draft.category,
        keyword: draft.keyword,
        query: draft.query.trim(),
        code,
        default_parameters: {
            [draft.execParamName || "parameter"]: draft.execParamValue,
        },
        status: "generated",
        apiStatus: "generated",
        provider: draft.provider,
        tokenToolId: draft.tokenToolId,
        recommendationQuery: recommendation,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
    };
}

function formatNow() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}:${String(d.getSeconds()).padStart(2, "0")}`;
}

const FIELD_CONTROL_STYLES = {
    input: {
        fontSize: 12,
        fontWeight: 400,
        fontFamily: '"Noto Sans KR", sans-serif',
        color: "#333333",
    },
} as const;

function KatexPreview({ latex }: { latex: string }) {
    const html = useMemo(() => {
        try {
            return katex.renderToString(latex, { throwOnError: false, displayMode: true });
        } catch {
            return latex;
        }
    }, [latex]);

    return <Box dangerouslySetInnerHTML={{ __html: html }} />;
}

function VisualGuidePanel({
    icon,
    title,
    desc,
}: {
    icon: ReactNode;
    title: string;
    desc: string;
}) {
    return (
        <Box className={classes.visualPanelBody}>
            <Stack align="center" gap={0}>
                <Box className={classes.execGuideIcon}>{icon}</Box>
                <Text className={classes.visualFallbackTitle}>{title}</Text>
                <Text className={classes.visualFallbackDesc}>{desc}</Text>
            </Stack>
        </Box>
    );
}

function traceLineClass(line: string): string {
    if (line.startsWith("[SUCCESS]")) return classes.traceLineSuccess;
    if (line.startsWith("[SYSTEM]")) return classes.traceLineSystem;
    if (line.startsWith("[INFO]") || line.startsWith("[TRACE]")) return classes.traceLineInfo;
    if (line.startsWith("[ERROR]") || line.startsWith("[WARN]")) return classes.traceLineWarn;
    if (line.startsWith(">_")) return classes.traceLineMuted;
    return classes.traceLineInfo;
}

function appendAssetizeMockLogs(
    appendTraceLogs: (lines: string[]) => void,
    name: string,
) {
    appendTraceLogs([
        `[SYSTEM] Assetization request received for generated tool: '${name}'`,
        "[TRACE] Registering standard schema inside secure central repository...",
        "[TRACE] Creating secure container interface for execution mapping...",
        "[SUCCESS] Assetization successfully closed. Status -> 'assetized'",
    ]);
}

export default function ToolManagementPage() {
    const [lastUpdated, setLastUpdated] = useState(formatNow());
    const [isGenerating, setIsGenerating] = useState(false);
    const [isModifying, setIsModifying] = useState(false);
    const [isAssetizing, setIsAssetizing] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);
    const [secrets, setSecrets] = useState<SecretKeyItem[]>([]);
    const [secretsLoading, setSecretsLoading] = useState(false);
    const [tokenToolOptions, setTokenToolOptions] = useState<{ value: string; label: string }[]>([]);
    const [tokenToolsLoading, setTokenToolsLoading] = useState(false);

    const traceViewportRef = useRef<HTMLDivElement>(null);
    const prevTraceCountRef = useRef<number | null>(null);

    const { showSuccess, showWarning, showError, showInfo } = useNotifications();
    const { openConfirmModal } = useCommonModals();

    const {
        actions,
        buttons,
        formReadOnly,
        canExec,
        ...state
    } = useToolState();

    useEffect(() => {
        useToolManagementStore.getState().clearSelection();
    }, []);

    useEffect(() => {
        const count = state.traceLogs.length;
        if (prevTraceCountRef.current === null) {
            prevTraceCountRef.current = count;
            return;
        }
        if (count <= prevTraceCountRef.current) {
            prevTraceCountRef.current = count;
            return;
        }
        prevTraceCountRef.current = count;
        const el = traceViewportRef.current;
        if (el) {
            el.scrollTop = el.scrollHeight;
        }
    }, [state.traceLogs]);

    const {
        data: toolQueryData,
        isLoading: isToolListLoading,
        isError: isToolListError,
        refetch: refetchToolList,
    } = useTool();

    const applyToolListToStore = useCallback((res: ToolListResponse | undefined, failed: boolean) => {
        const store = useToolManagementStore.getState();
        if (failed || !res?.success) {
            if (!res?.success && res) {
                const technicalDetail = res.error ?? "목록 조회 실패";
                console.error("[ToolManagement] POST /tool/list/query failed:", technicalDetail, res);
            }
            store.setListError(LIST_LOAD_ERROR_MESSAGE);
            store.setListStatus("error");
            return;
        }

        const previousTools = store.tools;
        const listable = filterToolsForManagementList(res.result ?? []);
        const items = listable.map(tool => {
            const normalized = normalizeToolItem(tool);
            const previous = previousTools.find(t => t.tool_id === normalized.tool_id);
            return mergeToolListItemFromCache(normalized, previous);
        });
        store.setTools(sortToolListItems(items));
        store.setListError(null);
        store.setListStatus("success");
        setLastUpdated(formatNow());
    }, []);

    useEffect(() => {
        if (isToolListError) {
            console.error("[ToolManagement] POST /tool/list/query failed");
            applyToolListToStore(undefined, true);
            return;
        }

        if (toolQueryData) {
            applyToolListToStore(toolQueryData, false);
            return;
        }

        if (isToolListLoading) {
            const store = useToolManagementStore.getState();
            store.setListStatus("loading");
            store.setListError(null);
        }
    }, [toolQueryData, isToolListLoading, isToolListError, applyToolListToStore]);

    const loadTools = useCallback(async () => {
        const store = useToolManagementStore.getState();
        store.setListStatus("loading");
        store.setListError(null);
        try {
            const result = await refetchToolList();
            applyToolListToStore(result.data, result.isError || !result.data?.success);
        } catch (err) {
            const technicalDetail = err instanceof FetchAPIError
                ? parseToolApiError(err.data, "목록 조회 실패")
                : err instanceof Error
                    ? err.message
                    : "목록 조회 실패";
            console.error("[ToolManagement] POST /tool/list/query failed:", technicalDetail, err);
            applyToolListToStore(undefined, true);
        }
    }, [refetchToolList, applyToolListToStore]);

    useEffect(() => {
        let cancelled = false;

        const fetchSecrets = async () => {
            setSecretsLoading(true);
            try {
                const res = await secretList();
                if (cancelled) return;

                if (!res.success) {
                    console.error("[ToolManagement] POST /secret/list failed:", res.error, res);
                    setSecrets([]);
                    showWarning(res.error ?? "연계 기관 목록을 불러오지 못했습니다.");
                    return;
                }

                setSecrets(res.result ?? []);
            } catch (err) {
                if (cancelled) return;
                console.error("[ToolManagement] POST /secret/list failed:", err);
                setSecrets([]);
                showWarning("연계 기관 목록을 불러오지 못했습니다. API 연결(/secret/list)을 확인해 주세요.");
            } finally {
                if (!cancelled) setSecretsLoading(false);
            }
        };

        void fetchSecrets();

        return () => {
            cancelled = true;
        };
        // 마운트 시 1회만 조회 — showWarning 등 불안정 참조로 재호출 방지
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const secretOptions = useMemo(
        () => secrets.map(s => ({ value: s.secret_id, label: s.provider })),
        [secrets],
    );

    useEffect(() => {
        const secretId = state.formDraft.provider.trim();
        if (!secretId) {
            setTokenToolOptions([]);
            return;
        }

        let cancelled = false;
        setTokenToolsLoading(true);

        void toolListTokenTools(secretId)
            .then(res => {
                if (cancelled) return;
                if (!res.success) {
                    console.error("[ToolManagement] POST /tool/list/query (token tools) failed:", res.error, res);
                    setTokenToolOptions([]);
                    return;
                }
                const options = (res.result ?? []).map(t => ({
                    value: t.tool_id,
                    label: t.title?.trim() || t.tool_id,
                }));
                console.info("[ToolManagement] token tool options:", options);
                setTokenToolOptions(options);
            })
            .catch(err => {
                if (cancelled) return;
                console.error("[ToolManagement] token tool list failed:", err);
                setTokenToolOptions([]);
            })
            .finally(() => {
                if (!cancelled) setTokenToolsLoading(false);
            });

        return () => {
            cancelled = true;
        };
        // provider 변경 시에만 재조회 — showWarning 등 불안정 참조 제외
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [state.formDraft.provider]);

    const handleFieldChange = useCallback(
        (field: keyof typeof state.formDraft, value: string) => {
            actions.patchFormField({ [field]: value });
            actions.evaluateToolDirty();
        },
        [actions],
    );

    const handleSecretChange = useCallback(
        (secretId: string | null) => {
            actions.patchFormField({
                provider: secretId ?? "",
                tokenToolId: "",
            });
            actions.evaluateToolDirty();
        },
        [actions],
    );

    const handleSelectTool = useCallback(
        (tool: ToolListItem) => {
            actions.selectTool(tool);
        },
        [actions],
    );

    const handleListCreateNew = useCallback(() => {
        actions.createNewTool();
        showInfo("새로운 도구 정보 등록 모드가 시작되었습니다.");
    }, [actions, showInfo]);

    const handleListCollapse = useCallback(() => {
        actions.toggleLeftPanel(true);
    }, [actions]);

    const handleListReload = useCallback(() => {
        void loadTools();
    }, [loadTools]);

    const handleReset = useCallback(() => {
        const { changed } = actions.resetToOrigin();
        if (state.editorMode === "new") {
            actions.createNewTool();
            showInfo("새로운 도구 등록 폼이 활성화되었습니다.");
            return;
        }
        if (changed) {
            const title = useToolManagementStore.getState().formDraft.title;
            if (state.selectedToolId && title) {
                actions.resetExecPreview("selected", title);
            }
            showInfo("원래 도구 설정 데이터로 초기화되었습니다.");
        }
    }, [actions, state.editorMode, state.selectedToolId, showInfo]);

    const bindPreviewAfterGenerate = useCallback(
        async (
            toolId: string,
            caller?: string,
            options?: { title?: string; queryExamples?: string[] | null; execQuery?: string },
        ) => {
            const code = useToolManagementStore.getState().formDraft.code;
            const recommendation = options?.execQuery
                ?? resolveExecQueryText(options?.queryExamples, null, options?.title);
            try {
                const infoRes = await toolInfo(toolId);
                const inputs = infoRes.result?.funcs?.[0]?.inputs ?? [];
                const preview = resolveExecPreview(
                    caller,
                    inputs.map(i => ({
                        name: i.name,
                        properties: i.properties?.map(p => ({ name: p.name })),
                    })),
                    code,
                );
                actions.bindExecPreview(
                    preview.paramName,
                    preview.paramValue,
                    recommendation,
                );
            } catch {
                const preview = resolveExecPreview(caller, undefined, code);
                actions.bindExecPreview(
                    preview.paramName,
                    preview.paramValue,
                    recommendation,
                );
            }
        },
        [actions],
    );

    const runGenerate = useCallback(async (): Promise<{
        toolId: string;
        code: string;
        description?: string;
        caller?: string;
        msg?: string;
        queryExamples?: string[] | null;
    }> => {
        const store = useToolManagementStore.getState();
        const attempt = store.attemptSaveTool(store.tools);
        if (!attempt.allowed) {
            throw new Error(attempt.message);
        }

        const { formDraft } = store;
        const name = formDraft.title.trim();
        const payload = buildGeneratePayload(formDraft);
        console.info("[ToolManagement] POST /tool/generate payload:", payload);
        actions.appendTraceLog(`[SYSTEM] Initiating code AST verification for '${name}'...`);

        const res: ToolGenerateResponse = await toolGenerate(payload, {
            onEvent: event => {
                const line = mapToolSSEEventToTraceLine(event);
                if (line) actions.appendTraceLog(line);
            },
        });

        const toolId = res.tool_id ?? res.result?.tool_id;
        if (!toolId) {
            throw new Error(res.error ?? res.detail ?? "도구 생성에 실패했습니다.");
        }

        const generatedCode = res.result?.code ?? formDraft.code;
        store.markGenerated(toolId, generatedCode, res.result?.caller);
        console.info("[ToolManagement] generate completed → generated", {
            toolId,
            lifecycle: "generated",
            formDraft: useToolManagementStore.getState().formDraft,
        });

        return {
            toolId,
            code: generatedCode,
            description: res.result?.description,
            caller: res.result?.caller,
            msg: res.msg,
            queryExamples: res.result?.query_examples ?? null,
        };
    }, [actions]);

    const handleGenerate = useCallback(async () => {
        const attempt = actions.attemptSaveTool(state.tools);
        if (!attempt.allowed) {
            if (attempt.reason === "SCHEMA_ALREADY_EXISTS") {
                showWarning(SCHEMA_ALREADY_EXISTS_MESSAGE);
                return;
            }
            if (attempt.reason === "ALREADY_SAVED") {
                showWarning(ALREADY_SAVED_MESSAGE);
                return;
            }
            if (attempt.reason === "DUPLICATE_TITLE") {
                showWarning(attempt.message);
                return;
            }
            showError(attempt.message);
            return;
        }

        setIsGenerating(true);
        const preserveQuery = useToolManagementStore.getState().formDraft.query;
        try {
            const result = await runGenerate();

            await loadTools();

            const store = useToolManagementStore.getState();
            const draft = store.formDraft;
            const existing = store.tools.find(t => t.tool_id === result.toolId);

            const execQueryText = resolveExecQueryText(
                result.queryExamples,
                null,
                draft.title.trim(),
                existing?.recommendationQuery ?? null,
            );

            actions.finalizeAfterGenerate(result.toolId, {
                description: result.description,
                code: result.code,
                execQuery: execQueryText,
                preserveQuery,
                caller: result.caller,
            });

            const updatedDraft = useToolManagementStore.getState().formDraft;
            const listItem = buildGeneratedListItem(
                result.toolId,
                updatedDraft,
                result.code,
                execQueryText,
            );

            if (existing) {
                updateToolInList(result.toolId, {
                    title: listItem.title,
                    description: listItem.description,
                    category: listItem.category,
                    keyword: listItem.keyword,
                    query: preserveQuery.trim(),
                    code: listItem.code,
                    provider: listItem.provider,
                    tokenToolId: listItem.tokenToolId,
                    recommendationQuery: listItem.recommendationQuery,
                    status: "generated",
                    apiStatus: "generated",
                });
            } else {
                store.setTools(sortToolListItems([
                    { ...listItem, query: preserveQuery.trim() },
                    ...store.tools,
                ]));
            }

            actions.toggleLeftPanel(false);

            await bindPreviewAfterGenerate(result.toolId, result.caller, {
                title: draft.title.trim(),
                queryExamples: result.queryExamples,
                execQuery: execQueryText
                    ?? useToolManagementStore.getState().formDraft.execQuery,
            });

            actions.appendTraceLog(
                `[SUCCESS] Generate completed at ${formatTraceTimestamp()} — tool_id=${result.toolId}`,
            );
            actions.appendTraceLog(
                `[INFO] Server applied: description, code, exec_query | Preserved: save_query, title, category, keyword, provider`,
            );
            actions.setJsonPreview(buildGenerateResultPreview({
                toolId: result.toolId,
                title: updatedDraft.title,
                description: result.description ?? updatedDraft.description,
                codeLength: (result.code ?? updatedDraft.code).length,
                execQuery: execQueryText,
                preserveQuery,
                queryExamples: result.queryExamples,
                caller: result.caller,
            }));

            setLastUpdated(formatNow());

            showSuccess(result.msg ?? "도구 명세 생성이 정상적으로 완료되었습니다. 상태가 '생성등록'으로 갱신되었습니다.");
        } catch (err) {
            const technicalDetail = err instanceof FetchAPIError
                ? parseToolApiError(err.data, "도구 생성 중 오류가 발생했습니다.")
                : err instanceof Error
                    ? err.message
                    : "도구 생성 중 오류가 발생했습니다.";
            const toastMessage = err instanceof FetchAPIError
                ? parseToolApiErrorForToast(err.data, "도구 생성 중 오류가 발생했습니다.")
                : technicalDetail;
            console.error("[ToolManagement] POST /tool/generate failed:", technicalDetail, err);
            actions.appendTraceLog(`[ERROR] ${technicalDetail}`);
            showError(toastMessage);
            openConfirmModal({ title: "도구 생성 실패", content: toastMessage });
        } finally {
            setIsGenerating(false);
        }
    }, [
        actions,
        bindPreviewAfterGenerate,
        loadTools,
        openConfirmModal,
        runGenerate,
        showError,
        showSuccess,
        showWarning,
        state.formDraft.title,
        state.tools,
    ]);

    const handleModify = useCallback(async () => {
        const toolId = state.pendingToolId ?? state.selectedToolId;
        if (!toolId) return;

        const store = useToolManagementStore.getState();
        const attempt = store.attemptSaveTool(store.tools);
        if (!attempt.allowed && attempt.reason === "VALIDATION_FAILED") {
            showError(attempt.message);
            return;
        }

        setIsModifying(true);
        const preserveQuery = store.formDraft.query;
        const { formDraft } = store;
        const name = formDraft.title.trim();

        try {
            actions.appendTraceLog(`[SYSTEM] Re-compiling generated tool '${name}' with updated specifications...`);

            const updatePayload = buildUpdateApiPayload(formDraft, toolId);
            console.info("[ToolManagement] PATCH /tool/update payload:", updatePayload);
            const res = await toolUpdate(updatePayload, {
                onEvent: event => {
                    const line = mapToolSSEEventToTraceLine(event);
                    if (line) actions.appendTraceLog(line);
                },
            });

            await loadTools();

            const freshStore = useToolManagementStore.getState();
            const existing = freshStore.tools.find(t => t.tool_id === toolId);
            const serverResult = res.result;

            const serverCode = serverResult?.code ?? formDraft.code;
            const execQueryText = resolveExecQueryText(
                serverResult?.query_examples ?? null,
                null,
                name,
                existing?.recommendationQuery ?? null,
            );

            actions.finalizeAfterGenerate(toolId, {
                description: serverResult?.description,
                code: serverCode,
                execQuery: execQueryText,
                preserveQuery,
                caller: serverResult?.caller ?? freshStore.callerScript ?? undefined,
            });

            const updatedDraft = useToolManagementStore.getState().formDraft;

            updateToolInList(toolId, {
                title: name,
                description: updatedDraft.description,
                category: updatedDraft.category,
                keyword: updatedDraft.keyword,
                query: preserveQuery.trim(),
                code: updatedDraft.code,
                provider: updatedDraft.provider,
                tokenToolId: updatedDraft.tokenToolId,
                recommendationQuery: execQueryText ?? updatedDraft.execQuery,
                status: "generated",
                apiStatus: "generated",
            });

            await bindPreviewAfterGenerate(toolId, serverResult?.caller ?? freshStore.callerScript ?? undefined, {
                title: name,
                queryExamples: serverResult?.query_examples ?? null,
                execQuery: execQueryText ?? updatedDraft.execQuery,
            });

            actions.appendTraceLog(
                `[SUCCESS] Update completed at ${formatTraceTimestamp()} — tool_id=${toolId}`,
            );
            actions.appendTraceLog(
                `[INFO] Server applied: description, code, exec_query | Preserved: save_query, title, category, keyword, provider`,
            );
            actions.setJsonPreview(buildToolSyncResultPreview({
                phase: "update",
                endpoint: "PATCH /tool/update",
                toolId,
                title: name,
                description: serverResult?.description ?? updatedDraft.description,
                codeLength: updatedDraft.code.length,
                execQuery: execQueryText,
                preserveQuery,
                queryExamples: serverResult?.query_examples ?? null,
                caller: serverResult?.caller ?? freshStore.callerScript ?? undefined,
            }));

            setLastUpdated(formatNow());
            showSuccess(res.msg ?? `'${name}' 도구의 생성 명세 수정이 완료되었습니다.`);
        } catch (err) {
            const technicalDetail = err instanceof FetchAPIError
                ? parseToolApiError(err.data, "도구 수정 중 오류가 발생했습니다.")
                : err instanceof Error
                    ? err.message
                    : "도구 수정 중 오류가 발생했습니다.";
            const toastMessage = err instanceof FetchAPIError
                ? parseToolApiErrorForToast(err.data, "도구 수정 중 오류가 발생했습니다.")
                : technicalDetail;
            console.error("[ToolManagement] PATCH /tool/update failed:", technicalDetail, err);
            actions.appendTraceLog(`[ERROR] ${technicalDetail}`);
            showError(toastMessage);
            openConfirmModal({ title: "도구 수정 실패", content: toastMessage });
        } finally {
            setIsModifying(false);
        }
    }, [actions, bindPreviewAfterGenerate, loadTools, openConfirmModal, showError, showSuccess, state.pendingToolId, state.selectedToolId]);

    const handleAssetizeSave = useCallback(async () => {
        const attempt = actions.attemptAssetizeTool(state.tools);
        if (!attempt.allowed) {
            if (attempt.reason === "SCHEMA_ALREADY_EXISTS") {
                showWarning(SCHEMA_ALREADY_EXISTS_MESSAGE);
                return;
            }
            if (attempt.reason === "DUPLICATE_TITLE") {
                showWarning(attempt.message);
                return;
            }
            showError(attempt.message);
            return;
        }

        const toolId = state.pendingToolId ?? state.selectedToolId;
        if (!toolId) {
            showError("저장된 tool_id가 없습니다. [도구생성]을 먼저 진행해 주세요.");
            return;
        }

        setIsAssetizing(true);
        const preserveQuery = useToolManagementStore.getState().formDraft.query;
        const { formDraft } = useToolManagementStore.getState();
        const preserveProvider = formDraft.provider.trim();
        const preserveTokenToolId = formDraft.tokenToolId.trim();
        try {
            appendAssetizeMockLogs(actions.appendTraceLogs, formDraft.title.trim());

            const assetPath = buildAssetPath(toolId);
            const assetizePayload = buildAssetizeApiPayload(formDraft, toolId, assetPath);
            console.info("[ToolManagement] POST /tool/assetize payload:", assetizePayload);
            const assetRes = await toolAssetize(assetizePayload);

            if (!assetRes.success) {
                throw new Error(assetRes.error ?? assetRes.detail ?? "도구 저장(자산화)에 실패했습니다.");
            }

            const resolvedPath = assetRes.result?.asset_path ?? assetPath;
            await loadTools();

            const freshStore = useToolManagementStore.getState();
            const saved = freshStore.tools.find(t => t.tool_id === toolId);

            actions.finalizeAfterGenerate(toolId, {
                preserveQuery,
                caller: freshStore.callerScript ?? undefined,
                lifecycleStatus: "assetized",
                assetPath: resolvedPath,
            });

            const updatedDraft = useToolManagementStore.getState().formDraft;

            updateToolInList(toolId, {
                title: updatedDraft.title.trim(),
                description: updatedDraft.description,
                category: updatedDraft.category,
                keyword: updatedDraft.keyword,
                query: preserveQuery.trim(),
                code: updatedDraft.code,
                provider: preserveProvider || updatedDraft.provider,
                tokenToolId: preserveTokenToolId || updatedDraft.tokenToolId,
                recommendationQuery: saved?.recommendationQuery ?? updatedDraft.execQuery,
                status: "assetized",
                apiStatus: "assetized",
            });

            actions.appendTraceLog(
                `[SUCCESS] Assetize completed — tool_id=${toolId}, asset_path=${resolvedPath}`,
            );
            actions.appendTraceLog(
                `[INFO] Preserved locally: secret_id(provider), tokenToolId, save_query | Server status -> assetized`,
            );

            actions.captureOriginCache(useToolManagementStore.getState().formDraft);
            showSuccess("도구가 영구 분석 에셋으로 라이브러리에 저장(자산화) 완료되었습니다.");
        } catch (err) {
            const message =
                err instanceof FetchAPIError
                    ? String(
                          (err.data as { error?: string; detail?: string })?.error
                          ?? (err.data as { detail?: string })?.detail
                          ?? "도구 저장 중 오류가 발생했습니다.",
                      )
                    : err instanceof Error
                        ? err.message
                        : "도구 저장 중 오류가 발생했습니다.";
            actions.appendTraceLog(`[ERROR] ${message}`);
            openConfirmModal({ title: "도구 저장 실패", content: message });
        } finally {
            setIsAssetizing(false);
        }
    }, [actions, loadTools, openConfirmModal, showError, showSuccess, showWarning, state]);

    const handleDelete = useCallback(() => {
        const toolId = state.selectedToolId ?? state.pendingToolId;
        if (!toolId) return;

        const tool = state.tools.find(t => t.tool_id === toolId);
        const title = tool?.title ?? state.formDraft.title;

        openConfirmModal({
            title: "도구 삭제",
            content: `정말 '${title}' 도구를 삭제하시겠습니까? 삭제 시 기존 보고서 생성 워크플로우에서 참조할 수 없게 됩니다.`,
            onConfirm: async () => {
                setIsDeleting(true);
                try {
                    await toolDelete(toolId);
                    actions.setTools(state.tools.filter(t => t.tool_id !== toolId));
                    actions.clearSelection();
                    actions.toggleLeftPanel(false);
                    showInfo("선택된 도구가 삭제되었습니다.");
                    setLastUpdated(formatNow());
                } catch (err) {
                    const detail =
                        err instanceof FetchAPIError
                            ? (err.data as { detail?: string })?.detail
                            : undefined;
                    openConfirmModal({
                        title: "삭제 실패",
                        content: detail ?? "도구 삭제 중 오류가 발생했습니다.",
                    });
                } finally {
                    setIsDeleting(false);
                }
            },
        });
    }, [actions, openConfirmModal, showInfo, state]);

    const handleExec = useCallback(async () => {
        const attempt = actions.attemptExecTool();
        if (!attempt.allowed) {
            showWarning(attempt.message);
            return;
        }

        const toolId = state.pendingToolId ?? state.selectedToolId;
        if (!toolId) {
            showWarning("실행할 도구가 선택되지 않았습니다.");
            return;
        }

        const query = state.formDraft.execQuery.trim();
        if (!query) {
            showWarning("실행용 테스트 질의어를 입력해 주세요.");
            return;
        }

        actions.setExecStatus("running");
        actions.setConsoleStatus("running");

        const hasTokenTool = Boolean(state.formDraft.tokenToolId.trim());
        const execTools = buildToolExecTools(toolId, state.formDraft.tokenToolId);
        const execPayload = {
            tools: execTools,
            query,
        };

        actions.appendTraceLog(`[INFO] POST /tool/exec — tools=[${execTools.join(", ")}]`);
        actions.appendTraceLog(`[TRACE] query payload: ${query.slice(0, 200)}${query.length > 200 ? "…" : ""}`);

        actions.setJsonPreview(buildExecRequestPreview({
            toolId,
            tokenToolId: state.formDraft.tokenToolId,
            query,
            tools: execTools,
        }));

        try {
            console.info("[ToolManagement] POST /tool/exec payload:", execPayload);

            const res = await toolExec(execPayload);

            if (!res.success) {
                const rawError = res.error ?? "실행 실패";
                const message = buildTokenExecErrorMessage(rawError, hasTokenTool);
                actions.appendTraceLog(`[ERROR] ${message}`);
                if (!hasTokenTool && isLikelyTokenAuthError(rawError)) {
                    actions.appendTraceLog(`[WARN] ${TOKEN_TOOL_EMPTY_HINT}`);
                }
                actions.setJsonPreview(buildExecResponsePreview({
                    toolId,
                    success: false,
                    result: null,
                    error: message,
                }));
                actions.setVisualResult({
                    type: "error",
                    message,
                });
                actions.setExecStatus("error");
                actions.setConsoleStatus("error");
                return;
            }

            const normalizedResult = normalizeToolExecResult(res.result);
            actions.setJsonPreview(buildExecResponsePreview({
                toolId,
                success: true,
                result: normalizedResult,
            }));
            actions.setVisualResult(parseExecVisualResult(normalizedResult));
            actions.setExecStatus("done");
            actions.setConsoleStatus("success");
            actions.appendTraceLog("[SUCCESS] Response fetched: 200 OK");
            showSuccess("실시간 연산 미리보기가 성공적으로 완성되었습니다.");
        } catch (err) {
            const rawMessage =
                err instanceof FetchAPIError
                    ? String(
                          (err.data as { error?: string })?.error
                          ?? (err.data as { detail?: string })?.detail
                          ?? "도구 실행 중 오류가 발생했습니다.",
                      )
                    : err instanceof Error
                        ? err.message
                        : "도구 실행 중 오류가 발생했습니다.";
            const message = buildTokenExecErrorMessage(rawMessage, hasTokenTool);
            actions.appendTraceLog(`[ERROR] ${message}`);
            if (!hasTokenTool && isLikelyTokenAuthError(rawMessage)) {
                actions.appendTraceLog(`[WARN] ${TOKEN_TOOL_EMPTY_HINT}`);
            }
            actions.setJsonPreview(buildExecResponsePreview({
                toolId,
                success: false,
                result: null,
                error: message,
            }));
            actions.setVisualResult({ type: "error", message });
            actions.setExecStatus("error");
            actions.setConsoleStatus("error");
        }
    }, [actions, showSuccess, showWarning, state]);

    const fieldClass = (field: RequiredFormField) =>
        state.validationErrors[field] ? classes.fieldError : undefined;

    const categoryOptions = useMemo(() => populateCategoryOptions(), []);

    const showTokenEmptyHint =
        state.editorMode !== "idle"
        && Boolean(state.formDraft.provider.trim())
        && !state.formDraft.tokenToolId.trim();

    const tokenHintClass =
        state.lifecycleStage === "generated" || state.lifecycleStage === "assetized"
            ? classes.tokenToolHint
            : classes.tokenToolHintMuted;

    const consoleStatusClass =
        state.consoleStatus === "running" ? classes.consoleStatusRunning
        : state.consoleStatus === "success" ? classes.consoleStatusSuccess
        : classes.consoleStatusReady;

    const consoleStatusText =
        state.consoleStatus === "running" ? "RUNNING"
        : state.consoleStatus === "success" ? "SUCCESS"
        : "HOST READY";

    const statusBar = (
        <div className={classes.pageStatusBar}>
            <span className={classes.pageStatusTimestamp}>
                최종 빌드 시간: {lastUpdated}
            </span>
            <span style={{ display: "flex", alignItems: "center" }}>
                <span className={classes.pipelineStatusDot} />
                <span className={classes.pipelineStatusText}>
                    로컬 보안 연산 시스템 가동 중
                </span>
            </span>
        </div>
    );

    const renderVisual = () => {
        const { visualResult, editorMode } = state;

        if (editorMode === "idle") {
            return (
                <VisualGuidePanel
                    icon={<IconPointer size={14} />}
                    title="도구를 선택해 주세요"
                    desc={VISUAL_SELECT_GUIDE_DESC}
                />
            );
        }

        if (!visualResult || visualResult.type === "empty") {
            if (state.execStatus === "done" && visualResult?.message) {
                return (
                    <Box className={classes.visualPanelBody} p="sm" style={{ width: "100%" }}>
                        <Text
                            size="xs"
                            component="pre"
                            style={{ whiteSpace: "pre-wrap", textAlign: "left", width: "100%" }}
                        >
                            {visualResult.message}
                        </Text>
                    </Box>
                );
            }
            return (
                <VisualGuidePanel
                    icon={<IconPlayerPlay size={14} />}
                    title="도구를 실행해 주세요"
                    desc={VISUAL_EXEC_GUIDE_DESC}
                />
            );
        }

        if (visualResult.type === "error") {
            const hasTokenTool = Boolean(state.formDraft.tokenToolId.trim());
            const rawMessage = visualResult.message ?? "도구 실행에 실패했습니다.";
            const showTokenGuide = !hasTokenTool && isLikelyTokenAuthError(rawMessage);

            if (showTokenGuide) {
                return (
                    <Box className={classes.visualPanelBody}>
                        <Box className={classes.tokenExecErrorPanel}>
                            <Text className={classes.tokenExecErrorTitle}>실행 오류 — 인증·토큰 확인 필요</Text>
                            <Text className={classes.tokenExecErrorDesc}>
                                {buildTokenExecErrorMessage(rawMessage, false)}
                            </Text>
                        </Box>
                    </Box>
                );
            }

            return (
                <VisualGuidePanel
                    icon={<IconPlayerPlay size={14} />}
                    title="실행 오류"
                    desc={rawMessage}
                />
            );
        }

        if (visualResult.type === "formula" && visualResult.latex) {
            return (
                <Box className={classes.visualPanelBody} style={{ overflowX: "auto" }}>
                    <KatexPreview latex={visualResult.latex} />
                </Box>
            );
        }

        if (visualResult.type === "dataset" && visualResult.tableRows && visualResult.tableHeaders) {
            return (
                <Box p="sm" style={{ width: "100%", overflowX: "auto" }}>
                    <Table className={classes.resultTable}>
                        <Table.Thead>
                            <Table.Tr>
                                {visualResult.tableHeaders.map(h => (
                                    <Table.Th key={h}>{h}</Table.Th>
                                ))}
                            </Table.Tr>
                        </Table.Thead>
                        <Table.Tbody>
                            {visualResult.tableRows.map((row, idx) => (
                                <Table.Tr key={idx}>
                                    {visualResult.tableHeaders!.map(h => (
                                        <Table.Td key={h}>{String(row[h] ?? "")}</Table.Td>
                                    ))}
                                </Table.Tr>
                            ))}
                        </Table.Tbody>
                    </Table>
                </Box>
            );
        }

        return (
            <Box className={classes.visualPanelBody}>
                <Text size="xs" c="dimmed">{visualResult.message}</Text>
            </Box>
        );
    };

    return (
        <DefaultAppPageLayout
            icon={<IconSettings size={20} />}
            buttons={statusBar}
        >
            <Box className={`${classes.workspace} ${state.leftPanelCollapsed ? classes.workspaceCollapsed : ""}`}>
                <ToolListPanel
                    tools={state.tools}
                    listStatus={state.listStatus}
                    selectedToolId={state.selectedToolId}
                    collapsed={state.leftPanelCollapsed}
                    onSelectTool={handleSelectTool}
                    onCreateNew={handleListCreateNew}
                    onReload={handleListReload}
                    onCollapse={handleListCollapse}
                />

                {/* RIGHT: 상세 + 콘솔 */}
                <Box className={classes.rightColumn}>
                    <Box className={classes.rightFormPanel}>
                        <Box className={classes.panelHeader}>
                            <Group gap={6}>
                                {state.leftPanelCollapsed && (
                                    <button
                                        type="button"
                                        className={classes.expandBtn}
                                        title="목록 보이기"
                                        onClick={() => actions.toggleLeftPanel(false)}
                                    >
                                        <IconChevronsRight size={14} />
                                    </button>
                                )}
                                <Text className={classes.panelHeaderTitle}>{state.formTitle}</Text>
                            </Group>
                            <div className={classes.headerActions}>
                                {buttons.showReset && (
                                    <Button
                                        size="xs"
                                        variant="default"
                                        leftSection={<IconArrowBackUp size={11} />}
                                        onClick={handleReset}
                                        styles={{ label: { fontSize: "10px", fontWeight: 700 } }}
                                    >
                                        초기화
                                    </Button>
                                )}
                                {buttons.showDelete && (
                                    <Button
                                        size="xs"
                                        variant="light"
                                        color="red"
                                        leftSection={<IconTrash size={11} />}
                                        loading={isDeleting}
                                        onClick={handleDelete}
                                        styles={{ label: { fontSize: "10px", fontWeight: 700 } }}
                                    >
                                        삭제
                                    </Button>
                                )}
                                {buttons.showCreate && (
                                    <Button
                                        size="xs"
                                        color="blue"
                                        leftSection={<IconSettings size={11} />}
                                        loading={isGenerating}
                                        onClick={() => void handleGenerate()}
                                        styles={{ label: { fontSize: "10px", fontWeight: 700 } }}
                                    >
                                        도구생성
                                    </Button>
                                )}
                                {buttons.showModify && (
                                    <Button
                                        size="xs"
                                        color="sageBlue"
                                        leftSection={<IconPencil size={11} />}
                                        loading={isModifying}
                                        onClick={() => void handleModify()}
                                        disabled={formReadOnly}
                                        styles={{ label: { fontSize: "10px", fontWeight: 700 } }}
                                    >
                                        도구수정
                                    </Button>
                                )}
                                {buttons.showSave && (
                                    <Button
                                        size="xs"
                                        color="teal"
                                        leftSection={<IconDeviceFloppy size={11} />}
                                        loading={isAssetizing}
                                        disabled={buttons.saveDisabled}
                                        onClick={() => void handleAssetizeSave()}
                                        styles={{ label: { fontSize: "10px", fontWeight: 700 } }}
                                    >
                                        도구저장
                                    </Button>
                                )}
                            </div>
                        </Box>

                        <Box className={classes.formBody}>
                            <Stack gap="sm">
                                <Box>
                                    <div className={classes.formFieldLabelRow}>
                                        <Text className={classes.fieldLabel}>
                                            도구명 (Function Name) <Text span c="red">*</Text>
                                        </Text>
                                        {state.editorMode === "existing"
                                            && (state.pendingToolId ?? state.selectedToolId) && (
                                            <CopyableListItemId
                                                inline
                                                label="도구 ID"
                                                value={state.pendingToolId ?? state.selectedToolId ?? ""}
                                                copiedMessage="도구 ID가 복사되었습니다."
                                            />
                                        )}
                                    </div>
                                    <TextInput
                                        size="xs"
                                        className={`${classes.placeholderInput} ${classes.formFieldInput}`}
                                        classNames={{ input: fieldClass("title") }}
                                        placeholder="예: get_domestic_stock_price"
                                        value={state.formDraft.title}
                                        onChange={e => handleFieldChange("title", e.currentTarget.value)}
                                        readOnly={formReadOnly}
                                        styles={FIELD_CONTROL_STYLES}
                                    />
                                </Box>

                                <Box>
                                    <Text className={classes.fieldLabel}>
                                        도구설명 <Text span c="red">*</Text>
                                    </Text>
                                    <Textarea
                                        size="xs"
                                        className={`${classes.placeholderInput} ${classes.formFieldInput}`}
                                        classNames={{ input: fieldClass("description") }}
                                        placeholder="한국투자증권 API를 연동하여 특정 국내 주식의 현재가, 등락율, 시가총액 및 주요 재무 지표를 실시간으로 조회합니다."
                                        rows={2}
                                        value={state.formDraft.description}
                                        onChange={e => handleFieldChange("description", e.currentTarget.value)}
                                        readOnly={formReadOnly}
                                        styles={FIELD_CONTROL_STYLES}
                                    />
                                </Box>

                                <Group grow align="flex-start" gap="sm">
                                    <Box style={{ flex: 4 }}>
                                        <Text className={classes.fieldLabel}>
                                            도구 카테고리 <Text span c="red">*</Text>
                                        </Text>
                                        <Select
                                            size="xs"
                                            data={categoryOptions}
                                            value={state.formDraft.category}
                                            onChange={v => handleFieldChange("category", v ?? DEFAULT_CATEGORY_CODE)}
                                            className={classes.formFieldInput}
                                            styles={FIELD_CONTROL_STYLES}
                                            classNames={{ input: fieldClass("category") }}
                                            disabled={formReadOnly}
                                        />
                                    </Box>
                                    <Box style={{ flex: 6 }}>
                                        <Text className={classes.fieldLabel}>
                                            연관 키워드 (쉼표 구분) <Text span c="red">*</Text>
                                        </Text>
                                        <TextInput
                                            size="xs"
                                            className={`${classes.placeholderInput} ${classes.formFieldInput}`}
                                            classNames={{ input: fieldClass("keyword") }}
                                            placeholder="예: 주식, 시세, 한국투자증권"
                                            value={state.formDraft.keyword}
                                            onChange={e => handleFieldChange("keyword", e.currentTarget.value)}
                                            readOnly={formReadOnly}
                                            styles={FIELD_CONTROL_STYLES}
                                        />
                                    </Box>
                                </Group>

                                <Box className={classes.providerRow}>
                                    <Box className={classes.providerRowField}>
                                        <Text className={classes.providerRowLabel}>
                                            API 연계 기관 (Provider)
                                        </Text>
                                        <Select
                                            size="xs"
                                            data={secretOptions}
                                            placeholder={secretsLoading ? "기관 목록 불러오는 중..." : "기관 검색 및 선택..."}
                                            value={state.formDraft.provider || null}
                                            onChange={handleSecretChange}
                                            className={classes.formFieldInput}
                                            styles={FIELD_CONTROL_STYLES}
                                            classNames={{ input: fieldClass("provider") }}
                                            disabled={formReadOnly || secretsLoading}
                                            searchable
                                            nothingFoundMessage="등록된 연계 기관이 없습니다."
                                        />
                                    </Box>
                                    <Box className={classes.providerRowField}>
                                        <Text className={classes.providerRowLabel}>
                                            {TOKEN_TOOL_FIELD_LABEL}
                                        </Text>
                                        <Select
                                            size="xs"
                                            data={tokenToolOptions}
                                            placeholder={
                                                !state.formDraft.provider.trim()
                                                    ? "연계 기관을 먼저 선택하세요"
                                                    : tokenToolsLoading
                                                        ? "토큰 도구 불러오는 중..."
                                                        : tokenToolOptions.length === 0
                                                            ? "등록된 토큰 도구 없음"
                                                            : "토큰 발급 도구 선택 (선택)"
                                            }
                                            value={state.formDraft.tokenToolId || null}
                                            onChange={v => handleFieldChange("tokenToolId", v ?? "")}
                                            className={classes.formFieldInput}
                                            styles={FIELD_CONTROL_STYLES}
                                            disabled={
                                                formReadOnly
                                                || !state.formDraft.provider.trim()
                                                || tokenToolsLoading
                                                || tokenToolOptions.length === 0
                                            }
                                            searchable
                                            clearable
                                            nothingFoundMessage="조건에 맞는 토큰 도구가 없습니다."
                                        />
                                    </Box>
                                </Box>
                                {showTokenEmptyHint && (
                                    <Text className={`${tokenHintClass} ${classes.providerRowHint}`}>
                                        {TOKEN_TOOL_EMPTY_HINT}
                                    </Text>
                                )}

                                <Box>
                                    <Text className={classes.fieldLabel}>
                                        도구 저장용 질의문 (Prompt Query) <Text span c="red">*</Text>
                                    </Text>
                                    <Textarea
                                        size="xs"
                                        className={`${classes.placeholderInput} ${classes.formFieldInput}`}
                                        classNames={{ input: fieldClass("query") }}
                                        placeholder="6자리 종목코드를 입력하면 해당 종목의 실시간 현재가, 전일비, 등락률, 시가, 고가, 저가, 거래량, 시가총액, PER, PBR 등을 JSON 형태로 반환해줘."
                                        rows={2}
                                        value={state.formDraft.query}
                                        onChange={e => handleFieldChange("query", e.currentTarget.value)}
                                        readOnly={formReadOnly}
                                        styles={FIELD_CONTROL_STYLES}
                                    />
                                </Box>

                                <Box>
                                    <Group justify="space-between" mb={6}>
                                        <Text className={classes.fieldLabel} mb={0}>
                                            도구 저장용 예시 코드 (Execution Script)
                                        </Text>
                                        <Text size="10px" c="dimmed" ff="monospace">python (mcp standard format)</Text>
                                    </Group>
                                    <Box className={classes.codeEditorWrap}>
                                        <Box className={classes.codeEditorTab}>
                                            <Group gap={6}>
                                                <IconSettings size={12} color="#60a5fa" />
                                                <span>
                                                    {state.formDraft.title
                                                        ? `${state.formDraft.title}.py`
                                                        : "new_analytic_tool.py"}
                                                </span>
                                            </Group>
                                        </Box>
                                        <ScrollArea
                                            className={classes.consoleScrollArea}
                                            h={240}
                                            styles={DARK_CONSOLE_SCROLL_STYLES}
                                            {...DARK_CONSOLE_SCROLL_PROPS}
                                        >
                                            <Textarea
                                                className={classes.codeTextarea}
                                                autosize
                                                minRows={10}
                                                value={state.formDraft.code}
                                                onChange={e => handleFieldChange("code", e.currentTarget.value)}
                                                readOnly={formReadOnly}
                                            />
                                        </ScrollArea>
                                    </Box>
                                </Box>
                            </Stack>
                        </Box>
                    </Box>

                    {/* SPLIT PANEL 1: 트랜잭션 로그 콘솔 */}
                    <Box className={classes.consolePanel}>
                        {state.execStatus === "running" && (
                            <Box className={classes.execLoader}>
                                <Loader size="sm" color="blue" />
                                <Text size="xs" fw={700}>SAGE 런타임 호스트 연동 시퀀스 가동 중...</Text>
                            </Box>
                        )}
                        <Box className={classes.consoleHeader}>
                            <Group gap={8}>
                                <Box style={{
                                    background: "#dbeafe", color: "#2563eb",
                                    padding: 6, borderRadius: 6, display: "flex",
                                }}>
                                    <IconTerminal size={12} />
                                </Box>
                                <Box>
                                    <Text className={classes.panelHeaderTitle}>
                                        실시간 API 호출 및 트랜잭션 로그 콘솔
                                    </Text>
                                    <Text size="11px" c="dimmed">
                                        도구 저장 및 테스트 실행 시 내부 컴파일러와 원천 API 트래픽 로그를 추적합니다.
                                    </Text>
                                </Box>
                            </Group>
                        </Box>
                        <Box className={classes.consoleBody}>
                            <Box className={classes.consoleTraceColumn}>
                                <div className={classes.consoleSubHeader}>
                                    <span className={classes.consoleSubLabel}>standard system trace</span>
                                    <span className={consoleStatusClass}>{consoleStatusText}</span>
                                </div>
                                <ScrollArea
                                    className={classes.consoleTraceArea}
                                    h={180}
                                    viewportRef={traceViewportRef}
                                    styles={DARK_CONSOLE_SCROLL_STYLES}
                                    {...DARK_CONSOLE_SCROLL_PROPS}
                                >
                                    {state.traceLogs.map((line, idx) => (
                                        <div key={`${idx}-${line}`} className={`${classes.traceLogLine} ${traceLineClass(line)}`}>
                                            {line}
                                        </div>
                                    ))}
                                </ScrollArea>
                            </Box>
                            <Box className={classes.consoleJsonColumn}>
                                <div className={classes.consoleSubHeader}>
                                    <Group gap={4}>
                                        <IconBraces size={12} color="#818cf8" />
                                        <span className={classes.consoleSubLabel}>raw json response</span>
                                    </Group>
                                    <Text size="9px" fw={700} style={{
                                        background: "#1e293b", padding: "2px 6px",
                                        borderRadius: 4, fontFamily: "var(--sage-font-mono)", color: "#94a3b8",
                                    }}>
                                        application/json
                                    </Text>
                                </div>
                                <ScrollArea
                                    className={classes.consoleScrollArea}
                                    h={180}
                                    styles={DARK_CONSOLE_SCROLL_STYLES}
                                    {...DARK_CONSOLE_SCROLL_PROPS}
                                >
                                    <pre className={classes.jsonPreviewContent}>{state.jsonPreview}</pre>
                                </ScrollArea>
                            </Box>
                        </Box>
                    </Box>

                    {/* SPLIT PANEL 2: 알고리즘 검증 + 미리보기 */}
                    <Box className={`${classes.previewPanel} ${classes.previewDashboard}`}>
                        <Box className={classes.previewPanelHeader}>
                            <Group gap={8}>
                                <Box style={{
                                    background: "#d1fae5", color: "#059669",
                                    padding: 6, borderRadius: 6, display: "flex",
                                }}>
                                    <IconSquareRoot size={12} />
                                </Box>
                                <Box>
                                    <Text className={classes.panelHeaderTitle}>
                                        알고리즘 연산 모델 및 구조화 데이터셋 검증
                                    </Text>
                                    <Text size="11px" c="dimmed">
                                        API 응답 스키마와 내부 공식(Formula) 간의 정량적 정합도를 확인합니다.
                                    </Text>
                                </Box>
                            </Group>
                        </Box>

                        <Box className={classes.previewQuerySection}>
                            <Group justify="space-between" align="center" mb={8}>
                                <Text className={classes.fieldLabel} mb={0}>
                                    실행용 테스트 질의어 (Test Query for Preview)
                                </Text>
                                <Button
                                    size="xs"
                                    color="teal"
                                    leftSection={<IconBolt size={12} />}
                                    disabled={!canExec}
                                    loading={state.execStatus === "running"}
                                    onClick={() => void handleExec()}
                                    styles={{ label: { fontSize: "10px", fontWeight: 700 } }}
                                >
                                    미리보기 실행
                                </Button>
                            </Group>
                            <Box style={{ position: "relative" }}>
                                <Box style={{ position: "absolute", left: 12, top: 12, zIndex: 1, color: "#94a3b8" }}>
                                    <IconWand size={14} />
                                </Box>
                                <Textarea
                                    size="xs"
                                    className={`${classes.placeholderInput} ${classes.formFieldInput}`}
                                    placeholder={state.execQueryPlaceholder}
                                    rows={2}
                                    value={state.formDraft.execQuery}
                                    onChange={e => handleFieldChange("execQuery", e.currentTarget.value)}
                                    styles={{
                                        ...FIELD_CONTROL_STYLES,
                                        input: { ...FIELD_CONTROL_STYLES.input, paddingLeft: 36 },
                                    }}
                                    disabled={!canExec}
                                />
                            </Box>
                        </Box>

                        <Box className={classes.previewVisualBody}>
                            {renderVisual()}
                        </Box>
                    </Box>
                </Box>
            </Box>
        </DefaultAppPageLayout>
    );
}
