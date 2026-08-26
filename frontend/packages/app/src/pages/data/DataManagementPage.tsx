/**
 * DataManagementPage — Business Logic Full Implementation v3
 * ─────────────────────────────────────────────────────────────────
 * [비즈니스 로직]
 *   1. On Mount: 폼 초기화 + 데이터 분석 모델 목록(POST /api/data/list/query) + 도구 콤보박스 API 로드
 *   2. 신규 분석: 전체 State 클린 초기화
 *   3. 등록 유형 탭: 파일(100MB 검증) / 도구(미리보기 검증) / DB(플래그 off 시 UI 비노출)
 *   4. 삭제: 신규→초기화(Confirm) / 기존→DELETE /data/delete + JSON body + Toast·에러 메시지
 *   5. 통합 스키마 생성(Pangeaze): Pool 검증 → integrateModel(POST /data/pangeaze)
 *   6. 모델 저장(Read): saveModel stub — DATA_MODEL_SAVE_* 플래그 false, UI 미노출
 * [스타일]
 *   - 3분할 Flex 슬라이딩 (좌32% / 중·우 gap 24px) — 도구(API)관리 leftPanel 동일
 *   - Browse: 좌+중 / Detail: 중(sourceBinding+pool)+우(콘텐츠 높이)
 *   - CSS Module + Mantine (Tailwind 미사용)
 * ─────────────────────────────────────────────────────────────────
 */
import { useState, useMemo, useRef, useEffect, useCallback } from "react";
import {
    ActionIcon,
    Alert,
    Box,
    Button,
    Center,
    Checkbox,
    Flex,
    Group,
    Loader,
    Modal,
    ScrollArea,
    Select,
    Stack,
    Text,
    Textarea,
    TextInput,
} from "@mantine/core";
import {
    IconAlertCircle,
    IconBolt,
    IconCheck,
    IconChevronDown,
    IconChevronsLeft,
    IconChevronsRight,
    IconDatabase,
    IconDatabaseImport,
    IconFileSpreadsheet,
    IconPlayerPlay,
    IconPlugConnected,
    IconRefresh,
    IconTable,
    IconTerminal,
    IconTool,
    IconTrash,
    IconWand,
    IconX,
} from "@tabler/icons-react";
import { Dropzone, type FileRejection, MIME_TYPES } from "@mantine/dropzone";
import { useQuery } from "@tanstack/react-query";
import { DefaultAppPageLayout } from "@/layouts/appPage";
import { useDataList, useDeleteData } from "@/features/data";
import type { SageData } from "@/features/data";
import { FetchAPIError } from "@/features/Utils";
import { CSV_DEFAULT_SHEET_NAME, isCsvFormat } from "@/features/data/sourceSchema";
import { useUploadData } from "@/features/data-analysis";
import {
    DATA_CATEGORY_OPTIONS,
    DATA_MODEL_SAVE_UI_ENABLED,
    DATA_SOURCE_DB_TAB_ENABLED,
    MODEL_INFO_EMPTY_HINT,
    POOL_SOURCE_BINDING_HINT,
    SAVE_MODEL_NOT_AVAILABLE_MESSAGE,
    SCHEMA_EMPTY_PLACEHOLDER,
    JSON_CONSOLE_FOLLOW_THRESHOLD_PX,
    JSON_CONSOLE_HEIGHT_DEFAULT,
    JSON_CONSOLE_HEIGHT_STREAMING,
} from "@/libs/stores/dataManagement/constants";
import {
    DataModelSaveNotEnabledError,
    integrateModel,
    saveModel,
    useToolPreview,
    verifyDbConnection,
    extractPangeazeSchema,
    resolveSchemaPropertyMap,
    buildToolTitleMap,
} from "@/features/data-management";
import { useTool, toolInfo } from "@/features/tool";
import {
    pickExecQueryPlaceholder,
    resolveExecQueryText,
} from "@/features/tool-management/resolveQueryExamples";
import type { PangeazeResponse } from "@/features/data-analysis";
import { useCommonModals, useNotifications } from "@/hooks";
import { useDataManagementStore } from "@/libs/stores/DataManagementStore";
import {
    DUPLICATE_NAME_MESSAGE,
    DIRTY_MODAL_MESSAGE,
    SCHEMA_ALREADY_EXISTS_MESSAGE,
} from "@/libs/stores/dataManagement/dirtyGuardSlice";
import { normalizeToolId, poolItemsToDataSources } from "@/libs/stores/dataManagement/poolSlice";
import {
    useDataManagementActions,
    useDataManagementDerived,
    useDataManagementState,
} from "@/libs/stores/dataManagement/useDataManagementSelectors";
import { validateDbForm } from "@/libs/stores/dataManagement/dbValidators";
import {
    MAX_ANALYSIS_FIELD_LENGTH,
    normalizeUploadedFile,
    type DbColumnMeta,
    type DbForm,
    type DbVendor,
    type TabType,
} from "@/libs/stores/dataManagement/types";
import type { DbConnStatus } from "@/libs/stores/dataManagement/dbSlice";
import classes from "./datamanagement.module.css";
import { DARK_CONSOLE_SCROLL_STYLES } from "@/styles/darkConsoleScroll";
import DataListPanel from "./DataListPanel";
import { PoolConsoleList } from "./PoolConsoleList";

/* ════════════════════════════════════════════════════════════════
   Constants
   ════════════════════════════════════════════════════════════════ */
const DB_PLACEHOLDERS = {
    host:      "ex) 10.120.44.15",
    port:      "ex) 5432",
    dbName:    "ex) sage_master_db",
    tableName: "ex) public.stock_volume_ranks",
    username:  "ex) sage_reader",
    password:  "ex) ••••••••",
    query:     "SELECT * FROM table_name LIMIT 100;",
};

const DB_VENDOR_OPTIONS: { value: DbVendor; label: string }[] = [
    { value: "postgresql", label: "PostgreSQL" },
    { value: "mssql", label: "MS SQL Server" },
];

const FIELD_CONTROL_STYLES = {
    input: {
        fontSize: 12,
        fontWeight: 400,
        fontFamily: '"Noto Sans KR", sans-serif',
        color: "#333333",
    },
} as const;

const SCHEMA_JSON_PLACEHOLDER = `{
  "_hint": "통합 스키마 생성 후 JSON 매핑 결과가 표시됩니다."
}`;

/** 이하이면 스키마 테이블 전체 표기, 초과 시 스크롤 영역 + 안내 문구 */
const SCHEMA_TABLE_FULL_DISPLAY_LIMIT = 10;

const SCHEMA_TABLE_SCROLL_PROPS = {
    type: "scroll" as const,
    scrollbarSize: 6,
    offsetScrollbars: "y" as const,
};

const SCHEMA_TABLE_SCROLL_STYLES = {
    root: { flexShrink: 0 },
    viewport: { paddingRight: 4 },
    scrollbar: { background: "transparent" },
    thumb: { background: "rgba(148, 163, 184, 0.45)" },
} as const;

const JSON_CONSOLE_SCROLL_PROPS = {
    type: "scroll" as const,
    scrollbarSize: 6,
    offsetScrollbars: "y" as const,
};

const JSON_CONSOLE_SCROLL_STYLES = {
    ...DARK_CONSOLE_SCROLL_STYLES,
    root: { flexShrink: 0 },
    thumb: { background: "rgba(148, 163, 184, 0.45)" },
} as const;

const TOOL_PREVIEW_PLACEHOLDER = "// 도구를 선택하고 [미리보기 실행]을 눌러 결과를 확인하세요.";

/* ════════════════════════════════════════════════════════════════
   Helpers
   ════════════════════════════════════════════════════════════════ */
function formatNow() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")} ${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")}`;
}

function resolveDeleteErrorMessage(err: unknown): string {
    if (err instanceof FetchAPIError && err.data && typeof err.data === "object") {
        const data = err.data as {
            detail?: string | Array<{ msg?: string }>;
            error?: string;
        };
        if (typeof data.detail === "string" && data.detail.trim()) return data.detail;
        if (Array.isArray(data.detail)) {
            const joined = data.detail
                .map(item => item?.msg)
                .filter((msg): msg is string => Boolean(msg?.trim()))
                .join(" ");
            if (joined) return joined;
        }
        if (typeof data.error === "string" && data.error.trim()) return data.error;
    }
    if (err instanceof Error && err.message.trim()) return err.message;
    return "데이터셋 삭제 중 오류가 발생했습니다.";
}

type NewModeDraftSnapshot = {
    poolCount: number;
    analysisName: string;
    analysisDesc: string;
    hasFile: boolean;
    hasTool: boolean;
    hasDbHost: boolean;
    hasSchemaResult: boolean;
    hasStreamLogs: boolean;
    hasSuggestedQueries: boolean;
};

function hasNewModeDraftContent(snapshot: NewModeDraftSnapshot): boolean {
    return (
        snapshot.poolCount > 0
        || snapshot.analysisName.trim().length > 0
        || snapshot.analysisDesc.trim().length > 0
        || snapshot.hasFile
        || snapshot.hasTool
        || snapshot.hasDbHost
        || snapshot.hasSchemaResult
        || snapshot.hasStreamLogs
        || snapshot.hasSuggestedQueries
    );
}

/* ════════════════════════════════════════════════════════════════
   Sub-Component Props
   ════════════════════════════════════════════════════════════════ */
type ColumnMeta = { name: string; type: string };

type XlsxTabContentProps = {
    displayFilename: string | null;
    fileSizeLabel: string | null;
    isUploading: boolean;
    isCsvFile: boolean;
    readOnly?: boolean;
    onFilesAccepted: (files: File[]) => void;
    onFilesRejected: (rejections: FileRejection[]) => void;
    sheets: string[];
    columns: ColumnMeta[];
    selectedSheet: string;
    onSheetChange: (sheet: string) => void;
    sheetColumnMap: Record<string, boolean[]>;
    onColumnToggle: (sheet: string, colIdx: number) => void;
};

type ApiTabContentProps = {
    toolOptions: { value: string; label: string }[];
    selectedToolId: string | null;
    selectedToolLabel: string | null;
    onToolChange: (id: string | null) => void;
    toolDesc: string;
    execQuery: string;
    execQueryPlaceholder: string;
    onExecQueryChange: (value: string) => void;
    onPreviewClick: () => void;
    isToolLoading: boolean;
    isPreviewRunning: boolean;
    previewDisplay: string;
    readOnly?: boolean;
};

type DbTabContentProps = {
    isNewMode: boolean;
    dbForm: DbForm;
    dbColumns: DbColumnMeta[];
    onDbFormChange: (form: DbForm) => void;
    onVendorChange: (vendor: DbVendor) => void;
    onColumnToggle: (index: number) => void;
    isConnecting: boolean;
    connStatus: DbConnStatus;
    onVerify: () => void;
};

/* ════════════════════════════════════════════════════════════════
   Sub-Component: XlsxTabContent
   - 시트별 컬럼 선택 상태가 부모에서 관리되어 Sheet 이동 후에도 유지됨
   ════════════════════════════════════════════════════════════════ */
function XlsxTabContent({
    displayFilename, fileSizeLabel, isUploading, isCsvFile, readOnly = false,
    onFilesAccepted, onFilesRejected,
    sheets, columns,
    selectedSheet, onSheetChange,
    sheetColumnMap, onColumnToggle,
}: XlsxTabContentProps) {
    const currentCols = sheetColumnMap[selectedSheet] ?? columns.map(() => true);

    return (
        <Box>
            <Box p="md" pb="sm">
                <Dropzone
                    className={classes.dropzone}
                    onDrop={onFilesAccepted}
                    onReject={onFilesRejected}
                    accept={[MIME_TYPES.xlsx, MIME_TYPES.xls, MIME_TYPES.csv]}
                    maxSize={100 * 1024 * 1024}
                    multiple={false}
                    loading={isUploading}
                    disabled={readOnly}
                >
                    <Stack align="center" gap={6} className={classes.dropzoneInner}>
                        {isUploading ? (
                            <Loader size="sm" color="blue" />
                        ) : (
                            <IconDatabaseImport size={36} color="#60a5fa" />
                        )}
                        <Text size="sm" fw={600} className={classes.guideText}>
                            분석 대상 원천 파일 업로드
                        </Text>
                        <Text size="xs" className={classes.guideText}>
                            xls, xlsx, csv 포맷 지원 (최대 100MB)
                        </Text>
                        <Text size="xs" className={classes.guideText}>
                            클릭하거나 파일을 드래그 앤 드롭하세요
                        </Text>
                    </Stack>
                </Dropzone>
                {displayFilename && (
                    <Text size="xs" c="blue.6" ta="center" mt={6}>
                        {displayFilename}{fileSizeLabel}
                    </Text>
                )}
            </Box>

            <Box px="md" pb="sm">
                <Text className={classes.sectionLabel}>대상 시트 선택</Text>
                <Box className={classes.sheetSelectWrapper}>
                    {sheets.length === 0 ? (
                        <Text size="xs" className={classes.emptyGuideText} py={8}>
                            선택된 시트 정보가 없습니다.
                        </Text>
                    ) : isCsvFile ? (
                        <Stack gap={4}>
                            <Text size="xs" className={classes.guideText}>
                                CSV 파일은 시트 개념이 없으며 API 기본 시트명({CSV_DEFAULT_SHEET_NAME})으로 처리됩니다.
                            </Text>
                            <Checkbox
                                size="sm"
                                label={CSV_DEFAULT_SHEET_NAME}
                                checked
                                disabled
                                color="blue"
                            />
                        </Stack>
                    ) : (
                        <Stack gap={4}>
                            {sheets.map(sheet => (
                                <Checkbox
                                    key={sheet}
                                    size="sm"
                                    label={sheet}
                                    checked={selectedSheet === sheet}
                                    onChange={() => onSheetChange(sheet)}
                                    color="blue"
                                    disabled={readOnly}
                                />
                            ))}
                        </Stack>
                    )}
                </Box>
            </Box>

            <Box px="md" pb="md">
                <Group justify="space-between" mb={8}>
                    <Text className={classes.sectionLabel} style={{ marginBottom: 0 }}>
                        대상 컬럼 선택 및 타입 정합
                    </Text>
                    <Text size="10px" className={classes.guideText}>자동 메타 타입 매핑 진행됨</Text>
                </Group>
                <Box className={classes.columnSelectWrapper}>
                    <Box className={classes.columnTableHeader}>
                        <span className={classes.columnTableHeaderLabel}> </span>
                        <span className={classes.columnTableHeaderLabel}>컬럼명</span>
                        <span className={classes.columnTableHeaderLabel}>데이터 타입</span>
                    </Box>
                    <ScrollArea h={140} type="hover">
                        {columns.map((col, i) => (
                            <Box key={col.name} className={classes.columnTableRow}>
                                <Checkbox
                                    size="xs"
                                    checked={currentCols[i] ?? true}
                                    onChange={() => onColumnToggle(selectedSheet, i)}
                                    color="blue"
                                    disabled={readOnly}
                                />
                                <Text size="xs" c="dark.4" fw={500}>{col.name}</Text>
                                <Box>
                                    <span className={classes.columnTypeBadge}>{col.type}</span>
                                </Box>
                            </Box>
                        ))}
                    </ScrollArea>
                </Box>
            </Box>
        </Box>
    );
}

/* ════════════════════════════════════════════════════════════════
   Sub-Component: ApiTabContent
   - toolOptions: GET /api/tool/list 기반 실데이터
   - onPreviewClick: 부모에서 도구 선택 여부 검증 후 실행
   ════════════════════════════════════════════════════════════════ */
function ApiTabContent({
    toolOptions, selectedToolId, selectedToolLabel, onToolChange,
    toolDesc, execQuery, execQueryPlaceholder, onExecQueryChange,
    onPreviewClick, isToolLoading, isPreviewRunning,
    previewDisplay, readOnly = false,
}: ApiTabContentProps) {
    const canPreview = Boolean(selectedToolId) && !isToolLoading && !readOnly;
    const displayTitle = selectedToolLabel?.trim()
        || toolOptions.find(o => o.value === selectedToolId)?.label?.trim()
        || null;

    return (
        <Box>
            <Box p="md" pb="sm">
                <Select
                    size="sm"
                    className={classes.formFieldInput}
                    label="도구 목록 정보 조회 / 선택"
                    placeholder="도구를 선택하세요"
                    data={toolOptions}
                    value={selectedToolId}
                    onChange={onToolChange}
                    rightSection={<IconChevronDown size={14} />}
                    searchable
                    disabled={readOnly}
                    styles={FIELD_CONTROL_STYLES}
                />
            </Box>

            {selectedToolId && (
                <Box className={classes.apiToolCard}>
                    {isToolLoading ? (
                        <Center py="sm"><Loader size="xs" color="blue" /></Center>
                    ) : (
                        <>
                            <Box className={classes.apiToolCardHeader}>
                                <span className={classes.apiTypeBadge}>API / MCP</span>
                                <span className={classes.apiToolTitle}>
                                    {displayTitle ?? "도구 정보 조회 중..."}
                                </span>
                            </Box>
                            <span className={classes.apiToolIdMeta}>
                                도구 등록 ID : {selectedToolId}
                            </span>
                            <p className={classes.apiToolDesc}>
                                {toolDesc || "도구 설명 정보를 불러오는 중입니다..."}
                            </p>

                            <Box className={classes.previewQuerySection}>
                                <Group justify="space-between" align="center" mb={8}>
                                    <Text className={classes.fieldLabel} mb={0}>
                                        실행용 테스트 질의어 (Test Query for Preview)
                                    </Text>
                                    <Button
                                        size="xs"
                                        color="teal"
                                        leftSection={<IconBolt size={12} />}
                                        disabled={!canPreview}
                                        loading={isPreviewRunning}
                                        onClick={onPreviewClick}
                                        styles={{ label: { fontSize: 10, fontWeight: 700 } }}
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
                                        placeholder={execQueryPlaceholder || "도구 실행용 자연어 질의어를 입력하세요."}
                                        rows={2}
                                        value={execQuery}
                                        onChange={e => onExecQueryChange(e.currentTarget.value)}
                                        readOnly={readOnly}
                                        styles={{
                                            ...FIELD_CONTROL_STYLES,
                                            input: { ...FIELD_CONTROL_STYLES.input, paddingLeft: 36 },
                                        }}
                                        disabled={readOnly || !selectedToolId}
                                    />
                                </Box>
                            </Box>
                        </>
                    )}
                </Box>
            )}

            <Box className={classes.toolPreviewSection}>
                <div className={classes.toolPreviewTitle}>
                    <IconPlayerPlay size={12} color="#22c55e" />
                    도구 결과 실시간 미리보기
                </div>
                <Box className={classes.toolPreviewBox}>
                    <pre className={classes.toolPreviewBody}>{previewDisplay}</pre>
                </Box>
            </Box>
        </Box>
    );
}

/* ════════════════════════════════════════════════════════════════
   Sub-Component: DbTabContent
   - isNewMode=true  → placeholder 표시, readOnly=false (입력 가능)
   - isNewMode=false → 기존 데이터 로드 상태, readOnly=true (수정 금지)
   ════════════════════════════════════════════════════════════════ */
function DbTabContent({
    isNewMode, dbForm, dbColumns, onDbFormChange, onVendorChange,
    onColumnToggle, isConnecting, connStatus, onVerify,
}: DbTabContentProps) {
    const isReadOnly = !isNewMode;
    const vendorLabel = DB_VENDOR_OPTIONS.find(v => v.value === dbForm.vendor)?.label ?? "DB";

    const btnColor = connStatus === "success" ? "green" : connStatus === "error" ? "red" : "blue";
    const btnIcon = isConnecting
        ? <Loader size={12} />
        : connStatus === "success"
            ? <IconCheck size={12} />
            : <IconPlugConnected size={12} />;
    const btnLabel = isConnecting
        ? "연결 중..."
        : connStatus === "success"
            ? "연결 성공"
            : connStatus === "error"
                ? "연결 실패 — 재시도"
                : "DB 연결 및 스키마 검증";

    const set = (key: keyof DbForm) => (val: string) =>
        onDbFormChange({ ...dbForm, [key]: val });

    return (
        <Box>
            <Box className={classes.dbConnectorHeader}>
                <IconPlugConnected size={15} color="var(--mantine-color-sageBlue-7)" />
                <span className={classes.dbConnectorTitle}>
                    {vendorLabel} 실시간 커넥터 연결 설정
                </span>
            </Box>
            <p className={classes.dbConnectorDesc}>
                사내 인브레 격리 보안망 내 DB 테이블의 메타 스키마를 안전하게 파이프라인에 연결합니다.
                {isReadOnly && (
                    <Text span size="xs" c="orange.6" fw={600}> (등록된 모델 — 수정 잠금)</Text>
                )}
            </p>

            <Box px="md" pb="sm">
                <Text className={classes.sectionLabel}>DB 벤더 선택</Text>
                <Select
                    size="xs"
                    data={DB_VENDOR_OPTIONS}
                    value={dbForm.vendor}
                    onChange={v => v && onVendorChange(v as DbVendor)}
                    disabled={isReadOnly}
                    styles={FIELD_CONTROL_STYLES}
                />
            </Box>

            <Box className={classes.dbFormRow}>
                <Box>
                    <p className={classes.dbFieldLabel}>HOST *</p>
                    <TextInput size="xs" value={dbForm.host}
                        onChange={e => set("host")(e.currentTarget.value)}
                        placeholder={DB_PLACEHOLDERS.host}
                        readOnly={isReadOnly}
                        styles={FIELD_CONTROL_STYLES}
                    />
                </Box>
                <Box>
                    <p className={classes.dbFieldLabel}>PORT *</p>
                    <TextInput size="xs" value={dbForm.port}
                        onChange={e => set("port")(e.currentTarget.value)}
                        placeholder={dbForm.vendor === "mssql" ? "ex) 1433" : DB_PLACEHOLDERS.port}
                        readOnly={isReadOnly}
                        styles={FIELD_CONTROL_STYLES}
                    />
                </Box>
            </Box>

            <Box className={classes.dbFormRow}>
                <Box>
                    <p className={classes.dbFieldLabel}>DB NAME *</p>
                    <TextInput size="xs" value={dbForm.dbName}
                        onChange={e => set("dbName")(e.currentTarget.value)}
                        placeholder={DB_PLACEHOLDERS.dbName}
                        readOnly={isReadOnly}
                        styles={FIELD_CONTROL_STYLES}
                    />
                </Box>
                <Box>
                    <p className={classes.dbFieldLabel}>TABLE NAME *</p>
                    <TextInput size="xs" value={dbForm.tableName}
                        onChange={e => set("tableName")(e.currentTarget.value)}
                        placeholder={DB_PLACEHOLDERS.tableName}
                        readOnly={isReadOnly}
                        styles={FIELD_CONTROL_STYLES}
                    />
                </Box>
            </Box>

            <Box className={classes.dbFormRow}>
                <Box>
                    <p className={classes.dbFieldLabel}>USER *</p>
                    <TextInput size="xs" value={dbForm.username}
                        onChange={e => set("username")(e.currentTarget.value)}
                        placeholder={DB_PLACEHOLDERS.username}
                        readOnly={isReadOnly}
                        styles={FIELD_CONTROL_STYLES}
                    />
                </Box>
                <Box>
                    <p className={classes.dbFieldLabel}>PASSWORD *</p>
                    <TextInput size="xs" type="password" value={dbForm.password}
                        onChange={e => set("password")(e.currentTarget.value)}
                        placeholder={DB_PLACEHOLDERS.password}
                        readOnly={isReadOnly}
                        styles={FIELD_CONTROL_STYLES}
                    />
                </Box>
            </Box>

            <Box className={classes.dbFormField}>
                <p className={classes.dbFieldLabel}>SCHEMA FETCH QUERY (OPTIONAL)</p>
                <Textarea
                    size="xs"
                    className={classes.sqlQueryEditor}
                    value={dbForm.query}
                    onChange={e => set("query")(e.currentTarget.value)}
                    placeholder={DB_PLACEHOLDERS.query}
                    readOnly={isReadOnly}
                    minRows={4}
                />
            </Box>

            <Box px="md" pb="sm">
                <Button
                    size="sm" color={btnColor}
                    leftSection={btnIcon}
                    loading={isConnecting}
                    onClick={onVerify}
                    fullWidth
                    disabled={isReadOnly}
                >
                    {btnLabel}
                </Button>
            </Box>

            {dbColumns.length > 0 && (
                <Box px="md" pb="md">
                    <Group justify="space-between" mb={8}>
                        <Text className={classes.sectionLabel} style={{ marginBottom: 0 }}>
                            대상 컬럼 선택 및 타입 정합
                        </Text>
                        <Text size="10px" className={classes.guideText}>쿼리 결과 기반 자동 매핑</Text>
                    </Group>
                    <Box className={classes.columnSelectWrapper}>
                        <Box className={classes.columnTableHeader}>
                            <span className={classes.columnTableHeaderLabel}> </span>
                            <span className={classes.columnTableHeaderLabel}>컬럼명</span>
                            <span className={classes.columnTableHeaderLabel}>데이터 타입</span>
                        </Box>
                        <ScrollArea h={140} type="hover">
                            {dbColumns.map((col, i) => (
                                <Box key={col.name} className={classes.columnTableRow}>
                                    <Checkbox
                                        size="xs"
                                        checked={col.selected}
                                        onChange={() => onColumnToggle(i)}
                                        color="blue"
                                        disabled={isReadOnly}
                                    />
                                    <Text size="xs" c="dark.4" fw={500}>{col.name}</Text>
                                    <Box>
                                        <span className={classes.columnTypeBadge}>{col.type}</span>
                                    </Box>
                                </Box>
                            ))}
                        </ScrollArea>
                    </Box>
                </Box>
            )}
        </Box>
    );
}

/* ════════════════════════════════════════════════════════════════
   Main Page: DataManagementPage
   ════════════════════════════════════════════════════════════════ */
export default function DataManagementPage() {
    const {
        selectedData, activeTab, analysisName, analysisDesc, analysisCategory,
        errorMsg, saveStatus, schemaResult, saveDatasetsJson, suggestedQueries, streamLogs, isBuilding,
        consolePhase, poolItems, activePoolId, localFile, currentFile, selectedToolId, toolPreviewResult,
        isPreviewLoading, execQuery, execQueryPlaceholder,
        dbForm, isDbLocked, dbColumns, connStatus, isConnecting,
        dirtyModalOpen,
        leftPanelCollapsed, rightPanelVisible,
    } = useDataManagementState();

    const {
        setActiveTab, setAnalysisName, setAnalysisDesc, setAnalysisCategory, setErrorMsg,
        setSaveStatus, setSchemaResult, setSaveDatasetsJson, setSuggestedQueries, appendStreamLog,
        clearStreamLogs, setIsBuilding, setConsolePhase, resetAll, startNewAnalysis, hydrateFromModel,
        setUploadedFile, clearFile, setActiveSheetByName, toggleColumnByIndex,
        restoreFileFromPool, addFileToPool, addToolToPool, addDbToPool,
        removeFromPool, selectPoolItem, clearActivePoolItem, refreshPoolToolDisplayNames,
        setSelectedToolId, setToolPreviewResult,
        setPreviewLoading, setExecQuery, setExecQueryPlaceholder,
        updateDbField, setDbVendor, setDbColumns, toggleDbColumn,
        setConnStatus, setIsConnecting, restoreDbFromPool, clearDb, clearTool,
        evaluatePoolDirty, evaluateName,
        attemptSave, attemptBuildSchema, setHasActiveSchema, closeDirtyModal,
        enterDetailMode, enterBrowseMode, toggleLeftPanel, toggleRightPanel,
    } = useDataManagementActions();

    const {
        isNewMode, fileSheets, fileColumns, selectedSheet, sheetColumnMap,
    } = useDataManagementDerived();

    const [lastUpdated] = useState(formatNow());
    const [isFileUploading, setIsFileUploading] = useState(false);
    const [jsonJumpToLatest, setJsonJumpToLatest] = useState(false);
    const abortRef = useRef<AbortController | null>(null);
    const jsonScrollViewportRef = useRef<HTMLDivElement>(null);
    const jsonFollowTailRef = useRef(true);

    const scrollJsonConsoleToBottom = useCallback(() => {
        const viewport = jsonScrollViewportRef.current;
        if (!viewport) return;
        viewport.scrollTop = viewport.scrollHeight;
    }, []);

    const handleJumpToLatestLogs = useCallback(() => {
        jsonFollowTailRef.current = true;
        setJsonJumpToLatest(false);
        scrollJsonConsoleToBottom();
    }, [scrollJsonConsoleToBottom]);

    const { upload } = useUploadData();
    const { mutate: previewMutate, isPending: isPreviewPending } = useToolPreview();
    const { openConfirmModal } = useCommonModals();
    const { showWarning, showInfo, showError } = useNotifications();

    useEffect(() => {
        if (!DATA_SOURCE_DB_TAB_ENABLED && activeTab === "db") {
            setActiveTab("xlsx");
        }
    }, [activeTab, setActiveTab]);

    const {
        data: dataList = [],
        isLoading: isListLoading,
        isError: isListError,
        refetch: refetchDataList,
    } = useDataList();
    const { data: toolData } = useTool();
    const { mutate: deleteMutate, isPending: isDeleting } = useDeleteData();

    const displayList = dataList;

    const existingNames = useMemo(
        () => displayList.map(d => d.name),
        [displayList],
    );

    const { data: toolDetailData, isLoading: isToolDetailLoading } = useQuery({
        queryKey: ["tool", "info", selectedToolId ?? ""],
        queryFn: () => toolInfo(selectedToolId!),
        enabled: !!selectedToolId,
    });

    const toolSelectOptions = useMemo(
        () => (toolData?.result ?? []).map(t => ({ value: t.tool_id, label: t.title })),
        [toolData],
    );

    const toolTitleById = useMemo(() => {
        const map: Record<string, string> = {};
        for (const tool of toolData?.result ?? []) {
            const id = normalizeToolId(tool.tool_id ?? "");
            const title = tool.title?.trim();
            if (id && title) map[id] = title;
        }
        return map;
    }, [toolData]);

    const toolDesc = toolDetailData?.result?.description ?? "";

    const selectedToolLabel = useMemo(() => {
        if (!selectedToolId) return null;
        const normalizedId = normalizeToolId(selectedToolId);
        const fromList = toolSelectOptions.find(
            t => normalizeToolId(t.value) === normalizedId,
        )?.label?.trim();
        if (fromList) return fromList;
        const fromCatalog = toolTitleById[normalizedId];
        if (fromCatalog) return fromCatalog;
        const fromDetail = toolDetailData?.result?.title?.trim();
        if (fromDetail) return fromDetail;
        const fromPool = poolItems.find(
            p => p.type === "tool" && normalizeToolId(p.sealed.toolId) === normalizedId,
        );
        if (fromPool?.type === "tool" && fromPool.displayName !== fromPool.sealed.toolId) {
            return fromPool.displayName;
        }
        return null;
    }, [selectedToolId, toolSelectOptions, toolTitleById, toolDetailData, poolItems]);

    useEffect(() => {
        if (!selectedToolId) return;
        const listItem = toolData?.result?.find(t => t.tool_id === selectedToolId);
        const examples = listItem?.query_examples ?? null;
        const title = listItem?.title ?? selectedToolId;
        const placeholder = pickExecQueryPlaceholder(examples)
            ?? `${title} 도구를 활용한 자연어 미리보기 정합성 검증을 시동해줘.`;
        const initialQuery = resolveExecQueryText(examples, null, title) ?? "";
        setExecQueryPlaceholder(placeholder);
        setExecQuery(initialQuery);
        setToolPreviewResult(null);
    }, [selectedToolId, toolData, setExecQuery, setExecQueryPlaceholder, setToolPreviewResult]);

    useEffect(() => {
        if (!selectedData?.did) return;
        let cancelled = false;

        void buildToolTitleMap(selectedData.sources, toolTitleById).then((map) => {
            if (!cancelled) refreshPoolToolDisplayNames(map);
        });

        return () => {
            cancelled = true;
        };
    }, [selectedData?.did, selectedData?.sources, toolTitleById, refreshPoolToolDisplayNames]);

    const filteredList = displayList;
    const listPanelLoading = isListLoading && displayList.length === 0;
    const listPanelError = isListError && displayList.length === 0;

    const schemaFields = useMemo(() => {
        const propertyMap = resolveSchemaPropertyMap(schemaResult);
        return Object.entries(propertyMap).map(([name, schema]) => ({
            name,
            isPk: false,
            type: schema.type ?? "any",
            source: "Schema",
        }));
    }, [schemaResult]);

    const displayJson = useMemo(() => {
        if (saveDatasetsJson) return saveDatasetsJson;
        if (schemaResult) return JSON.stringify(schemaResult, null, 2);
        return SCHEMA_JSON_PLACEHOLDER;
    }, [saveDatasetsJson, schemaResult]);

    const hasJsonContent = Boolean(schemaResult || saveDatasetsJson);

    const showMappingConsole = consolePhase === "streaming" || isBuilding;
    const isStreamingLayout = isBuilding && showMappingConsole;
    const isViewMode = !isNewMode;
    const schemaTableNeedsScroll = schemaFields.length > SCHEMA_TABLE_FULL_DISPLAY_LIMIT;
    const jsonConsoleHeight = isStreamingLayout
        ? JSON_CONSOLE_HEIGHT_STREAMING
        : (hasJsonContent ? JSON_CONSOLE_HEIGHT_DEFAULT : 100);

    useEffect(() => {
        if (!showMappingConsole || !jsonFollowTailRef.current) return;
        scrollJsonConsoleToBottom();
    }, [streamLogs, showMappingConsole, scrollJsonConsoleToBottom]);

    useEffect(() => {
        if (!showMappingConsole) return;

        let detach: (() => void) | undefined;
        const frameId = requestAnimationFrame(() => {
            const viewport = jsonScrollViewportRef.current;
            if (!viewport) return;

            const onScroll = () => {
                const atBottom =
                    viewport.scrollHeight - viewport.clientHeight - viewport.scrollTop
                    <= JSON_CONSOLE_FOLLOW_THRESHOLD_PX;
                jsonFollowTailRef.current = atBottom;
                setJsonJumpToLatest(!atBottom && viewport.scrollHeight > viewport.clientHeight);
            };

            viewport.addEventListener("scroll", onScroll, { passive: true });
            detach = () => viewport.removeEventListener("scroll", onScroll);
        });

        return () => {
            cancelAnimationFrame(frameId);
            detach?.();
        };
    }, [showMappingConsole, isStreamingLayout]);

    useEffect(() => {
        if (isStreamingLayout) {
            jsonFollowTailRef.current = true;
            setJsonJumpToLatest(false);
        }
    }, [isStreamingLayout]);

    const toolPreviewDisplay = toolPreviewResult ?? TOOL_PREVIEW_PLACEHOLDER;

    const saveStatusLabel = saveStatus === "saving" || isBuilding
        ? "저장·생성 중..."
        : saveStatus === "success"
            ? "저장 완료"
            : schemaResult
                ? "정상 수립"
                : selectedData
                    ? "모델 로드됨"
                    : "대기 중";

    const runIntegrateStream = useCallback(async () => {
        abortRef.current?.abort();
        const controller = new AbortController();
        abortRef.current = controller;
        clearStreamLogs();
        setSchemaResult(null);
        setSaveDatasetsJson(null);
        setSuggestedQueries([]);
        setConsolePhase("streaming");
        setIsBuilding(true);
        setSaveStatus("saving");
        jsonFollowTailRef.current = true;
        setJsonJumpToLatest(false);
        enterDetailMode();

        const payload = {
            name: analysisName.trim(),
            description: analysisDesc.trim() || "(미입력)",
            query: "표준화된 데이터셋을 만들어줘",
            sources: poolItemsToDataSources(poolItems),
            category: analysisCategory,
        };

        try {
            const stream = await integrateModel(payload, controller.signal);
            for await (const chunk of stream) {
                if (controller.signal.aborted) break;
                if (typeof chunk === "string") {
                    appendStreamLog(`[ERROR] ${chunk}`);
                    continue;
                }
                const data = chunk as PangeazeResponse & Record<string, unknown>;
                if (data.msg) appendStreamLog(data.msg);

                if (Array.isArray(data.suggested_queries)) {
                    setSuggestedQueries(data.suggested_queries.filter(
                        (q): q is string => typeof q === "string" && q.trim().length > 0,
                    ));
                }

                const parsedSchema = extractPangeazeSchema(data);
                if (parsedSchema) {
                    setSchemaResult(parsedSchema);
                    setSaveDatasetsJson(JSON.stringify({ datasets: parsedSchema }, null, 2));
                    setConsolePhase("completed");
                    setHasActiveSchema(true);
                } else if (
                    data.eventType === "completed"
                    || data.eventType === "success"
                ) {
                    setConsolePhase("completed");
                }
            }
            setSaveStatus("success");
        } catch (error) {
            if (!(error instanceof DOMException && error.name === "AbortError")) {
                appendStreamLog(`[ERROR] ${String(error)}`);
                setSaveStatus("error");
            }
        } finally {
            setIsBuilding(false);
            const phase = useDataManagementStore.getState().consolePhase;
            if (phase === "streaming") setConsolePhase("idle");
        }
    }, [
        analysisName, analysisDesc, poolItems, clearStreamLogs, setSchemaResult,
        setSaveDatasetsJson, setSuggestedQueries, setConsolePhase, setHasActiveSchema,
        setIsBuilding, setSaveStatus, appendStreamLog, enterDetailMode,
    ]);

    const handleNewAnalysis = useCallback(() => {
        startNewAnalysis();
    }, [startNewAnalysis]);

    const applyPoolItemToTabs = useCallback((poolId: string) => {
        selectPoolItem(poolId);
        const item = useDataManagementStore.getState().poolItems.find(p => p.poolId === poolId);
        if (!item) return;

        if (item.type === "file") {
            setActiveTab("xlsx");
            restoreFileFromPool(item.sealed.hierarchy);
        } else if (item.type === "tool") {
            setActiveTab("api");
            setSelectedToolId(normalizeToolId(item.sealed.toolId));
        } else if (item.type === "db") {
            if (DATA_SOURCE_DB_TAB_ENABLED) {
                setActiveTab("db");
                restoreDbFromPool(item.sealed);
            }
        }
    }, [
        selectPoolItem, setActiveTab, restoreFileFromPool,
        setSelectedToolId, restoreDbFromPool,
    ]);

    const handleSelectData = useCallback(async (item: SageData) => {
        const enrichedMap = await buildToolTitleMap(item.sources, toolTitleById);
        hydrateFromModel(item, { toolTitleById: enrichedMap });
        enterDetailMode();
        queueMicrotask(() => {
            const first = useDataManagementStore.getState().poolItems[0];
            if (first) applyPoolItemToTabs(first.poolId);
        });
    }, [hydrateFromModel, enterDetailMode, applyPoolItemToTabs, toolTitleById]);

    const uploadExcelFile = useCallback((file: File) => {
        setErrorMsg(null);
        if (file.size > 100 * 1024 * 1024) {
            setErrorMsg(
                `파일 크기 초과: ${(file.size / 1024 / 1024).toFixed(1)}MB — 최대 100MB 이하 파일만 업로드 가능합니다.`,
            );
            return;
        }
        setIsFileUploading(true);
        upload.mutate({ file }, {
            onSuccess: (data) => {
                const node = normalizeUploadedFile(data);
                clearActivePoolItem();
                setUploadedFile(node, file);
                setIsFileUploading(false);
            },
            onError: (err) => {
                setErrorMsg(err.message ?? "파일 업로드 중 오류가 발생했습니다.");
                setIsFileUploading(false);
            },
        });
    }, [upload, clearActivePoolItem, setUploadedFile, setErrorMsg]);

    const handleFilesAccepted = useCallback((files: File[]) => {
        const file = files[0];
        if (file) uploadExcelFile(file);
    }, [uploadExcelFile]);

    const handleFilesRejected = useCallback((rejections: FileRejection[]) => {
        rejections.forEach(r => {
            const msg = r.errors[0]?.code === "file-too-large"
                ? `${r.file.name}: 최대 100MB 이하 파일만 업로드 가능합니다.`
                : `${r.file.name} 파일이 형식에 맞지 않습니다.`;
            showError(msg, { autoClose: 5000 });
        });
    }, [showError]);

    const uploadedDisplayName = localFile?.name ?? currentFile?.filename ?? null;
    const uploadedSizeLabel = localFile
        ? ` (${(localFile.size / 1024).toFixed(2)} KB)`
        : null;
    const isCsvFile = useMemo(
        () => isCsvFormat(
            currentFile?.fileType ?? "",
            currentFile?.path ?? localFile?.name ?? uploadedDisplayName ?? "",
        ),
        [currentFile, localFile, uploadedDisplayName],
    );

    const syncActivePoolFile = useCallback(() => {
        const state = useDataManagementStore.getState();
        if (!state.activePoolId || !state.currentFile) return;
        const item = state.poolItems.find(
            p => p.poolId === state.activePoolId && p.type === "file",
        );
        if (item) state.updateFileInPool(state.activePoolId, state.currentFile);
    }, []);

    const handleSheetChange = (sheetName: string) => {
        setActiveSheetByName(sheetName);
        queueMicrotask(() => {
            syncActivePoolFile();
            evaluatePoolDirty();
        });
    };

    const handleColumnToggle = (sheet: string, colIdx: number) => {
        toggleColumnByIndex(sheet, colIdx);
        queueMicrotask(() => {
            syncActivePoolFile();
            evaluatePoolDirty();
        });
    };

    const handlePreviewTool = () => {
        if (!selectedToolId) {
            setErrorMsg("도구를 먼저 선택한 후 미리보기를 실행해주세요.");
            return;
        }
        const query = execQuery.trim() || execQueryPlaceholder.trim();
        if (!query) {
            setErrorMsg("실행용 테스트 질의어를 입력해주세요.");
            return;
        }
        setErrorMsg(null);
        setPreviewLoading(true);
        previewMutate({ toolId: selectedToolId, query }, {
            onSuccess: (result) => {
                setToolPreviewResult(JSON.stringify(result, null, 2));
                setPreviewLoading(false);
            },
            onError: (err) => {
                setErrorMsg(err.message ?? "도구 미리보기 실행 중 오류가 발생했습니다.");
                setPreviewLoading(false);
            },
        });
    };

    const handleDbVerify = async () => {
        const validationError = validateDbForm(dbForm);
        if (validationError) {
            setErrorMsg(validationError);
            setConnStatus("error");
            return;
        }
        setErrorMsg(null);
        setIsConnecting(true);
        setConnStatus("connecting");
        try {
            const result = await verifyDbConnection(dbForm);
            setDbColumns(result.columns);
            setConnStatus("success");
        } catch (err) {
            setConnStatus("error");
            setErrorMsg(err instanceof Error ? err.message : "DB 연결 검증 중 오류가 발생했습니다.");
        } finally {
            setIsConnecting(false);
        }
    };

    const handleDbFormChange = (form: DbForm) => {
        (Object.keys(form) as (keyof DbForm)[]).forEach(key => {
            if (form[key] !== dbForm[key]) updateDbField(key, form[key]);
        });
    };

    const handleDbVendorChange = (vendor: DbVendor) => {
        setDbVendor(vendor);
    };

    const handleAddToPool = () => {
        setErrorMsg(null);

        if (activeTab === "xlsx") {
            if (!currentFile) {
                setErrorMsg("파일을 먼저 업로드해주세요.");
                return;
            }
            if (!addFileToPool(currentFile)) {
                const sheetName = currentFile.sheets.find(
                    s => s.id === currentFile.activeSheetId,
                )?.name ?? "";
                setErrorMsg(
                    `이미 Pool에 등록된 파일/시트 조합입니다: ${currentFile.filename}${sheetName ? ` / ${sheetName}` : ""}`,
                );
                return;
            }
        } else if (activeTab === "api") {
            if (!selectedToolId) {
                setErrorMsg("도구를 먼저 선택해주세요.");
                return;
            }
            const toolLabel = toolSelectOptions.find(t => t.value === selectedToolId)?.label ?? selectedToolId;
            if (!addToolToPool(selectedToolId, toolLabel)) {
                setErrorMsg("이미 Pool에 등록된 도구입니다.");
                return;
            }
        } else if (activeTab === "db" && DATA_SOURCE_DB_TAB_ENABLED) {
            const validationError = validateDbForm(dbForm);
            if (validationError) {
                setErrorMsg(validationError);
                return;
            }
            if (connStatus !== "success" || dbColumns.length === 0) {
                setErrorMsg("DB 연결 및 스키마 검증을 먼저 완료해주세요.");
                return;
            }
            const selectedCount = dbColumns.filter(c => c.selected).length;
            if (selectedCount === 0) {
                setErrorMsg("최소 1개 이상의 컬럼을 선택해주세요.");
                return;
            }
            const vendorLabel = DB_VENDOR_OPTIONS.find(v => v.value === dbForm.vendor)?.label ?? "DB";
            const displayName = `${dbForm.tableName} @ ${dbForm.host} (${vendorLabel})`;
            if (!addDbToPool({ ...dbForm, columns: dbColumns }, displayName)) {
                setErrorMsg("이미 Pool에 등록된 DB 소스입니다.");
                return;
            }
        }
        evaluatePoolDirty();
    };

    const handleRemoveFromPool = (poolId: string) => {
        const item = poolItems.find(p => p.poolId === poolId);
        const label = item?.displayName ?? "선택한 Pool 항목";

        openConfirmModal({
            title: "원천 소스 연동 해제",
            content: `"${label}"을(를) Pool에서 제거하면 해당 원천 소스 연동이 해제됩니다. 계속하시겠습니까?`,
            onConfirm: () => {
                removeFromPool(poolId);

                if (item?.type === "file" && currentFile?.id === item.sealed.fileId) {
                    clearFile();
                } else if (item?.type === "tool" && selectedToolId === normalizeToolId(item.sealed.toolId)) {
                    clearTool();
                } else if (item?.type === "db") {
                    const matchesActiveDb =
                        dbForm.host === item.sealed.host
                        && dbForm.dbName === item.sealed.dbName
                        && dbForm.tableName === item.sealed.tableName
                        && dbForm.vendor === item.sealed.vendor;
                    if (matchesActiveDb) {
                        clearDb();
                    }
                }

                evaluatePoolDirty();
                showInfo("Pool 항목이 제거되었습니다.");
            },
        });
    };

    const handlePoolItemClick = (poolId: string) => {
        applyPoolItemToTabs(poolId);
    };

    const handleDelete = useCallback(() => {
        setErrorMsg(null);

        if (isNewMode) {
            const draftSnapshot: NewModeDraftSnapshot = {
                poolCount: poolItems.length,
                analysisName,
                analysisDesc,
                hasFile: Boolean(currentFile || localFile),
                hasTool: Boolean(selectedToolId),
                hasDbHost: Boolean(dbForm.host?.trim()),
                hasSchemaResult: Boolean(schemaResult),
                hasStreamLogs: streamLogs.length > 0,
                hasSuggestedQueries: suggestedQueries.length > 0,
            };

            const runNewModeReset = () => {
                startNewAnalysis();
                showInfo("입력 내용이 초기화되었습니다.");
            };

            if (!hasNewModeDraftContent(draftSnapshot)) {
                runNewModeReset();
                return;
            }

            openConfirmModal({
                title: "신규 분석 초기화",
                content: "입력한 분석모델 정보와 Pool 항목이 모두 초기화됩니다. 계속하시겠습니까?",
                onConfirm: runNewModeReset,
            });
            return;
        }

        openConfirmModal({
            title: "데이터 분석 모델 삭제",
            content: `선택된 데이터 분석 모델을 삭제하시겠습니까?\n모델명: ${selectedData!.name}\n\n삭제 시 해당 모델을 참조하는 보고서·워크플로우에서 사용할 수 없게 될 수 있습니다.`,
            onConfirm: () => {
                deleteMutate(selectedData!.did, {
                    onSuccess: () => {
                        resetAll();
                        enterBrowseMode();
                        void refetchDataList();
                        showInfo("데이터 분석 모델이 삭제되었습니다.");
                    },
                    onError: (err: unknown) => {
                        const msg = resolveDeleteErrorMessage(err);
                        setErrorMsg(msg);
                        showWarning(msg);
                    },
                });
            },
        });
    }, [
        isNewMode, selectedData, poolItems.length, analysisName, analysisDesc,
        currentFile, localFile, selectedToolId, dbForm.host, schemaResult,
        streamLogs.length, suggestedQueries.length,
        deleteMutate, resetAll, startNewAnalysis, enterBrowseMode,
        openConfirmModal, refetchDataList, setErrorMsg, showWarning, showInfo,
    ]);

    const handleSaveModel = useCallback(async () => {
        setErrorMsg(null);
        const saveResult = attemptSave(analysisName);
        if (!saveResult.allowed) {
            if (saveResult.reason === "DUPLICATE_NAME") {
                showWarning(DUPLICATE_NAME_MESSAGE);
            }
            return;
        }
        if (!DATA_MODEL_SAVE_UI_ENABLED) {
            showInfo(SAVE_MODEL_NOT_AVAILABLE_MESSAGE, { autoClose: 4000 });
            return;
        }
        try {
            await saveModel({
                name: analysisName.trim(),
                description: analysisDesc.trim() || "(미입력)",
                sources: poolItemsToDataSources(poolItems),
                did: selectedData?.did,
            });
            void refetchDataList();
            showInfo("모델이 저장되었습니다.", { autoClose: 3000 });
        } catch (error) {
            if (error instanceof DataModelSaveNotEnabledError) {
                showInfo(SAVE_MODEL_NOT_AVAILABLE_MESSAGE, { autoClose: 4000 });
                return;
            }
            setErrorMsg(error instanceof Error ? error.message : "모델 저장 중 오류가 발생했습니다.");
        }
    }, [
        analysisName, analysisDesc, poolItems, selectedData?.did,
        attemptSave, setErrorMsg, showWarning, showInfo, refetchDataList,
    ]);

    const handleBuildSchema = async () => {
        setErrorMsg(null);
        enterDetailMode();
        const buildResult = attemptBuildSchema();
        if (!buildResult.allowed) {
            if (buildResult.reason === "SCHEMA_ALREADY_EXISTS") {
                showWarning(SCHEMA_ALREADY_EXISTS_MESSAGE, { autoClose: 4000 });
                return;
            }
            if (buildResult.reason === "EMPTY_NAME") {
                setErrorMsg("분석모델명을 먼저 입력해주세요.");
                return;
            }
            if (buildResult.reason === "EMPTY_POOL") {
                setErrorMsg("원천 에셋을 Pool에 최소 1개 이상 추가한 후 통합 스키마를 생성하세요.");
                return;
            }
            return;
        }
        const saveResult = attemptSave(analysisName);
        if (!saveResult.allowed) {
            if (saveResult.reason === "DUPLICATE_NAME") {
                showWarning(DUPLICATE_NAME_MESSAGE);
            }
            return;
        }
        await runIntegrateStream();
        void refetchDataList();
        const postSave = useDataManagementStore.getState();
        if (postSave.selectedData) {
            postSave.setPoolFromModel(postSave.poolItems);
            postSave.captureBaseline(postSave.selectedData.did, postSave.analysisName.trim());
        }
    };

    const handleAnalysisNameChange = (value: string) => {
        setAnalysisName(value, existingNames);
        evaluateName(value, existingNames);
    };

    const handleListCollapse = useCallback(() => {
        toggleLeftPanel(true);
    }, [toggleLeftPanel]);

    const handleRightPanelCollapse = useCallback(() => {
        toggleRightPanel(false);
    }, [toggleRightPanel]);

    const handleRightPanelExpand = useCallback(() => {
        toggleRightPanel(true);
    }, [toggleRightPanel]);

    /* ── Page Status Bar ── */
    const statusBar = (
        <div className={classes.pageStatusBar}>
            <span className={classes.pageStatusTimestamp}>
                최종 갱신: {lastUpdated}
            </span>
            <span style={{ display: "flex", alignItems: "center" }}>
                <span className={classes.pipelineStatusDot} />
                <span className={classes.pipelineStatusText}>
                    데이터 파이프라인 가동 가능
                </span>
            </span>
        </div>
    );

    return (
        <DefaultAppPageLayout icon={<IconDatabaseImport size={20} />} buttons={statusBar}>

            {/* ── 글로벌 에러 알림 배너 ── */}
            {errorMsg && (
                <Alert
                    icon={<IconAlertCircle size={16} />}
                    color="red"
                    variant="light"
                    mb="sm"
                    withCloseButton
                    onClose={() => setErrorMsg(null)}
                    styles={{ message: { fontSize: "12px" } }}
                >
                    {errorMsg}
                </Alert>
            )}

            <Box className={`${classes.workspace} ${leftPanelCollapsed ? classes.workspaceCollapsed : ""}`}>

                <DataListPanel
                    items={filteredList}
                    isLoading={listPanelLoading}
                    isError={listPanelError}
                    selectedDid={selectedData?.did ?? null}
                    toolTitleById={toolTitleById}
                    collapsed={leftPanelCollapsed}
                    onSelect={handleSelectData}
                    onCreateNew={handleNewAnalysis}
                    onReload={() => void refetchDataList()}
                    onCollapse={handleListCollapse}
                />

                <Box className={`${classes.detailColumn} ${!rightPanelVisible ? classes.detailColumnSingle : ""}`}>
                <Box className={classes.centerColumnStack}>
                    {/* SPLIT PANEL 1: 원천 에셋 바인딩 (폼 + 등록 유형 탭) */}
                    <Box className={classes.sourceBindingPanel}>
                    <Box className={classes.panelHeader}>
                        <Group gap={6}>
                            {leftPanelCollapsed && (
                                <button
                                    type="button"
                                    className={classes.expandBtn}
                                    title="목록 보이기"
                                    onClick={() => toggleLeftPanel(false)}
                                >
                                    <IconChevronsRight size={14} />
                                </button>
                            )}
                            <Text className={classes.panelHeaderTitle}>
                                데이터 분석 모델 상세 등록
                            </Text>
                        </Group>
                        <div className={classes.headerActions}>
                            {DATA_MODEL_SAVE_UI_ENABLED && (
                                <Button
                                    size="xs" variant="outline" color="blue"
                                    onClick={() => void handleSaveModel()}
                                    disabled={isViewMode}
                                    styles={{ label: { fontSize: "10px", fontWeight: 700 } }}
                                >
                                    모델 저장
                                </Button>
                            )}
                            <Button
                                size="xs" variant="outline" color="red"
                                leftSection={<IconTrash size={11} />}
                                onClick={handleDelete}
                                loading={isDeleting}
                                styles={{ label: { fontSize: "10px", fontWeight: 700 } }}
                            >
                                {isNewMode ? "초기화" : "삭제"}
                            </Button>
                        </div>
                    </Box>

                    <Box className={classes.formSection}>
                            <Box mb="sm">
                                <Text className={classes.fieldLabel}>
                                    분석모델명 <Text span c="red">*</Text>
                                </Text>
                                <TextInput
                                    size="xs"
                                    className={classes.formFieldInput}
                                    placeholder="분석모델명을 입력하세요"
                                    maxLength={MAX_ANALYSIS_FIELD_LENGTH}
                                    value={analysisName}
                                    onChange={e => handleAnalysisNameChange(e.currentTarget.value)}
                                    readOnly={isViewMode}
                                    styles={FIELD_CONTROL_STYLES}
                                />
                            </Box>
                            <Box mb="sm">
                                <Text className={classes.fieldLabel}>
                                    분석모델 설명 <Text span c="red">*</Text>
                                </Text>
                                <Textarea
                                    size="xs"
                                    className={classes.formFieldInput}
                                    placeholder="데이터셋에 대한 설명을 입력하세요"
                                    rows={3}
                                    maxLength={MAX_ANALYSIS_FIELD_LENGTH}
                                    value={analysisDesc}
                                    onChange={e => setAnalysisDesc(e.currentTarget.value)}
                                    readOnly={isViewMode}
                                    styles={FIELD_CONTROL_STYLES}
                                />
                            </Box>
                            <Box className={classes.categoryFieldWrap}>
                                <Text className={classes.fieldLabel}>
                                    데이터 카테고리 <Text span c="red">*</Text>
                                </Text>
                                <Select
                                    size="xs"
                                    className={`${classes.formFieldInput} ${classes.categorySelect}`}
                                    placeholder="카테고리"
                                    data={[...DATA_CATEGORY_OPTIONS]}
                                    value={analysisCategory}
                                    onChange={v => v && setAnalysisCategory(v as typeof analysisCategory)}
                                    comboboxProps={{ withinPortal: true }}
                                    disabled={isViewMode}
                                />
                            </Box>
                        </Box>

                        {/* ── 등록 유형 탭 그룹 ── */}
                        <Box className={classes.tabGroupSection} pb="sm">
                            <div className={classes.tabGroupLabel}>
                                등록 유형 선택 (원천 에셋 바인딩)
                            </div>
                            <div
                                className={`${classes.tabGroupWrapper} ${!DATA_SOURCE_DB_TAB_ENABLED ? classes.tabGroupWrapperDual : ""}`}
                            >
                                <button
                                    type="button"
                                    className={activeTab === "xlsx" ? classes.tabGroupBtnActive : classes.tabGroupBtn}
                                    onClick={() => setActiveTab("xlsx")}
                                    disabled={isViewMode}
                                >
                                    <IconFileSpreadsheet size={13} color="#059669" />
                                    파일 (Excel)
                                </button>
                                <button
                                    type="button"
                                    className={activeTab === "api" ? classes.tabGroupBtnActive : classes.tabGroupBtn}
                                    onClick={() => setActiveTab("api")}
                                    disabled={isViewMode}
                                >
                                    <IconTool size={13} color="#3b82f6" />
                                    도구 (API)
                                </button>
                                {DATA_SOURCE_DB_TAB_ENABLED && (
                                    <button
                                        type="button"
                                        className={activeTab === "db" ? classes.tabGroupBtnActive : classes.tabGroupBtn}
                                        onClick={() => setActiveTab("db")}
                                        disabled={isViewMode}
                                    >
                                        <IconDatabase size={13} color="#6366f1" />
                                        DB (SQL)
                                    </button>
                                )}
                            </div>
                        </Box>

                        {/* 탭 콘텐츠 */}
                        <Box className={classes.tabContentArea}>
                            {activeTab === "xlsx" && (
                                <XlsxTabContent
                                    displayFilename={uploadedDisplayName}
                                    fileSizeLabel={uploadedSizeLabel}
                                    isUploading={isFileUploading}
                                    isCsvFile={isCsvFile}
                                    readOnly={isViewMode}
                                    onFilesAccepted={handleFilesAccepted}
                                    onFilesRejected={handleFilesRejected}
                                    sheets={fileSheets}
                                    columns={fileColumns}
                                    selectedSheet={selectedSheet}
                                    onSheetChange={handleSheetChange}
                                    sheetColumnMap={sheetColumnMap}
                                    onColumnToggle={handleColumnToggle}
                                />
                            )}
                            {activeTab === "api" && (
                                <ApiTabContent
                                    toolOptions={toolSelectOptions}
                                    selectedToolId={selectedToolId}
                                    selectedToolLabel={selectedToolLabel}
                                    onToolChange={setSelectedToolId}
                                    toolDesc={toolDesc}
                                    execQuery={execQuery}
                                    execQueryPlaceholder={execQueryPlaceholder}
                                    onExecQueryChange={setExecQuery}
                                    onPreviewClick={handlePreviewTool}
                                    isToolLoading={isToolDetailLoading}
                                    isPreviewRunning={isPreviewPending || isPreviewLoading}
                                    previewDisplay={toolPreviewDisplay}
                                    readOnly={isViewMode}
                                />
                            )}
                            {activeTab === "db" && DATA_SOURCE_DB_TAB_ENABLED && (
                                <DbTabContent
                                    isNewMode={!isDbLocked && isNewMode}
                                    dbForm={dbForm}
                                    dbColumns={dbColumns}
                                    onDbFormChange={handleDbFormChange}
                                    onVendorChange={handleDbVendorChange}
                                    onColumnToggle={toggleDbColumn}
                                    isConnecting={isConnecting}
                                    connStatus={connStatus}
                                    onVerify={() => void handleDbVerify()}
                                />
                            )}
                        </Box>
                    </Box>

                    {/* SPLIT PANEL 2: 스키마 통합 Pool + 생성 오퍼레이션 */}
                    <Box className={`${classes.poolConsolePanel} ${isStreamingLayout ? classes.poolConsolePanelCompact : ""}`}>
                        <Box className={classes.poolConsoleHeader}>
                            <Group gap={8} style={{ flex: 1, minWidth: 0 }}>
                                <Box className={classes.poolConsoleIcon}>
                                    <IconTerminal size={12} />
                                </Box>
                                <Box style={{ minWidth: 0 }}>
                                    <Text className={classes.panelHeaderTitle}>
                                        스키마 통합 대상 Pool
                                    </Text>
                                    <Text size="11px" c="dimmed">
                                        {isStreamingLayout
                                            ? `${poolItems.length}건 적재됨 · 생성 로그는 우측 「연산 결과 JSON」에서 확인`
                                            : POOL_SOURCE_BINDING_HINT}
                                    </Text>
                                </Box>
                            </Group>
                            <Group gap={8} className={classes.poolConsoleActions} wrap="nowrap">
                                {!rightPanelVisible && (
                                    <button
                                        type="button"
                                        className={classes.expandBtn}
                                        title="통합 스키마 결과 보기"
                                        onClick={handleRightPanelExpand}
                                    >
                                        <IconChevronsLeft size={14} />
                                    </button>
                                )}
                                <Button
                                    size="xs" color="dark"
                                    leftSection={<IconRefresh size={11} />}
                                    onClick={handleAddToPool}
                                    disabled={isViewMode}
                                >
                                    Pool에 추가
                                </Button>
                                <Button
                                    size="xs" color="blue"
                                    className={classes.buildSchemaBtn}
                                    leftSection={isBuilding ? <Loader size={11} color="white" /> : <IconBolt size={11} />}
                                    onClick={() => void handleBuildSchema()}
                                    disabled={isBuilding || isViewMode}
                                >
                                    {isBuilding ? "생성·저장 중..." : "통합 스키마 생성"}
                                </Button>
                            </Group>
                        </Box>
                        {!isStreamingLayout && (
                        <Box className={classes.poolConsoleBody}>
                            {poolItems.length === 0 ? (
                                <Box className={classes.poolListEmpty}>
                                    <Text size="xs" className={classes.emptyGuideText}>
                                        원천 에셋을 Pool에 추가하세요
                                    </Text>
                                </Box>
                            ) : (
                                <PoolConsoleList
                                    items={poolItems}
                                    activePoolId={activePoolId}
                                    onItemClick={handlePoolItemClick}
                                    onRemove={isViewMode ? undefined : handleRemoveFromPool}
                                />
                            )}
                        </Box>
                        )}
                    </Box>
                </Box>

                <Box className={`${classes.rightPanel} ${!rightPanelVisible ? classes.rightPanelHidden : ""} ${isStreamingLayout ? classes.rightPanelStreaming : ""}`}>
                    <Box className={classes.panelHeader}>
                        <Group gap={6} style={{ flex: 1, minWidth: 0 }}>
                            <button
                                type="button"
                                className={classes.collapseBtn}
                                title="결과 패널 접기"
                                onClick={handleRightPanelCollapse}
                            >
                                <IconChevronsRight size={14} />
                            </button>
                            <Box style={{
                                width: 8, height: 8, borderRadius: "50%",
                                background: "#3b82f6", flexShrink: 0,
                            }} />
                            <Text className={classes.panelHeaderTitle}>
                                통합 스키마 빌드 결과
                            </Text>
                        </Group>
                        <Box className={classes.schemaStatusBadge}>
                            {saveStatusLabel}
                        </Box>
                    </Box>

                    {isStreamingLayout && (
                        <Box className={classes.streamingModeBanner}>
                            <Text size="xs" fw={600}>
                                스키마 생성 진행 중 — 아래 연산 로그를 확인하세요
                            </Text>
                        </Box>
                    )}

                    {!isStreamingLayout && selectedData && !schemaResult && (
                        <Box className={classes.modelInfoCard}>
                            <div className={classes.modelInfoRow}>
                                <span className={classes.modelInfoLabel}>모델명</span>
                                <span className={classes.modelInfoValue}>{selectedData.name}</span>
                            </div>
                            <div className={classes.modelInfoRow}>
                                <span className={classes.modelInfoLabel}>DID</span>
                                <span className={classes.modelInfoValue}>{selectedData.did}</span>
                            </div>
                            <div className={classes.modelInfoRow}>
                                <span className={classes.modelInfoLabel}>상태</span>
                                <span className={classes.modelInfoValue}>{selectedData.status || "-"}</span>
                            </div>
                            <Text size="xs" c="dimmed" mt={6}>
                                {MODEL_INFO_EMPTY_HINT}
                            </Text>
                        </Box>
                    )}

                    {!isStreamingLayout && (
                    <Box className={classes.schemaSectionCard}>
                        <Box className={classes.schemaMetaRow}>
                            <span className={classes.schemaMetaTitle}>
                                통합 스키마 표준 매핑 ({schemaFields.length}건)
                            </span>
                            {selectedData?.did && (
                                <span className={classes.schemaMetaDid}>
                                    DID: {selectedData.did}
                                </span>
                            )}
                        </Box>

                        {schemaFields.length > 0 ? (
                            <>
                                {schemaTableNeedsScroll && (
                                    <Text className={classes.schemaScrollHint}>
                                        전체 {schemaFields.length}건 · 스크롤하여 확인
                                    </Text>
                                )}
                                <Box className={classes.schemaTableHeader}>
                                    <span className={classes.schemaColLabel}>컬럼 ID</span>
                                    <span className={classes.schemaColLabel}>타입</span>
                                    <span className={classes.schemaColLabel} style={{ textAlign: "right" }}>
                                        매핑 원천
                                    </span>
                                </Box>
                                {schemaTableNeedsScroll ? (
                                    <ScrollArea
                                        className={classes.schemaTableScroll}
                                        h={280}
                                        styles={SCHEMA_TABLE_SCROLL_STYLES}
                                        {...SCHEMA_TABLE_SCROLL_PROPS}
                                    >
                                        {schemaFields.map(field => (
                                            <Box key={field.name} className={classes.schemaTableRow}>
                                                <span className={classes.schemaFieldName}>{field.name}</span>
                                                <span className={classes.schemaFieldType}>{field.type}</span>
                                                <span className={classes.schemaFieldSource}>{field.source}</span>
                                            </Box>
                                        ))}
                                    </ScrollArea>
                                ) : (
                                    <Box className={classes.schemaTableBody}>
                                        {schemaFields.map(field => (
                                            <Box key={field.name} className={classes.schemaTableRow}>
                                                <span className={classes.schemaFieldName}>{field.name}</span>
                                                <span className={classes.schemaFieldType}>{field.type}</span>
                                                <span className={classes.schemaFieldSource}>{field.source}</span>
                                            </Box>
                                        ))}
                                    </Box>
                                )}
                            </>
                        ) : (
                            <Box className={classes.schemaEmptyState}>
                                <IconTable size={28} style={{ color: "#cbd5e1" }} />
                                <Text size="xs" className={classes.emptyGuideText} lh={1.6} ta="center">
                                    {SCHEMA_EMPTY_PLACEHOLDER}
                                </Text>
                            </Box>
                        )}
                    </Box>
                    )}

                    <Box className={`${classes.jsonConsoleSection} ${isStreamingLayout ? classes.jsonConsoleSectionStreaming : ""}`}>
                        <Box className={classes.consoleCardWrapper}>
                            <Box className={classes.consoleCardLabel}>
                                <span className={classes.consoleCardTitle}>연산 결과 JSON</span>
                                <Group gap={6} wrap="nowrap">
                                    {jsonJumpToLatest && (
                                        <Button
                                            size="xs"
                                            variant="light"
                                            color="blue"
                                            onClick={handleJumpToLatestLogs}
                                            styles={{ label: { fontSize: "10px", fontWeight: 700 } }}
                                        >
                                            ↓ 최신 로그
                                        </Button>
                                    )}
                                    <Button
                                        size="xs" variant="subtle" color="blue"
                                        p={0} h="auto" style={{ fontSize: "10px" }}
                                        onClick={() => navigator.clipboard?.writeText(displayJson)}
                                    >
                                        복사
                                    </Button>
                                </Group>
                            </Box>

                            {showMappingConsole ? (
                                <Box className={`${classes.consoleCard} ${classes.consoleCardStreaming} ${isStreamingLayout ? classes.consoleCardStreamingActive : ""}`}>
                                    <ScrollArea
                                        className={classes.consoleJsonScrollArea}
                                        h={jsonConsoleHeight}
                                        viewportRef={jsonScrollViewportRef}
                                        styles={JSON_CONSOLE_SCROLL_STYLES}
                                        {...JSON_CONSOLE_SCROLL_PROPS}
                                    >
                                        <Box className={classes.terminalBody}>
                                            {streamLogs.map((log, i) => (
                                                <Box key={i} className={classes.terminalLine}>
                                                    <span className={classes.terminalPrompt}>›</span>
                                                    <span className={log.startsWith("[ERROR]") ? classes.terminalTextError : classes.terminalText}>
                                                        {log}
                                                    </span>
                                                </Box>
                                            ))}
                                            {isBuilding && (
                                                <Box className={classes.terminalLine}>
                                                    <span className={classes.terminalPrompt}>›</span>
                                                    <span className={classes.terminalCursor} />
                                                </Box>
                                            )}
                                        </Box>
                                    </ScrollArea>
                                </Box>
                            ) : (
                                <Box className={`${classes.consoleCard} ${hasJsonContent ? classes.consoleCardFilled : classes.consoleCardPlaceholder}`}>
                                    <ScrollArea
                                        className={classes.consoleJsonScrollArea}
                                        h={jsonConsoleHeight}
                                        styles={JSON_CONSOLE_SCROLL_STYLES}
                                        {...JSON_CONSOLE_SCROLL_PROPS}
                                    >
                                        <pre className={classes.consoleCardBody}>{displayJson}</pre>
                                    </ScrollArea>
                                </Box>
                            )}
                        </Box>

                        {!isStreamingLayout && (
                        <Box className={classes.suggestedQueriesBlock}>
                            <Box className={classes.schemaMetaRow}>
                                <span className={classes.schemaMetaTitle}>추천 질의문</span>
                                {suggestedQueries.length > 0 && (
                                    <span className={classes.consoleCardBadge}>
                                        {suggestedQueries.length}건
                                    </span>
                                )}
                            </Box>
                            {suggestedQueries.length > 0 ? (
                                <Box className={classes.suggestedQueriesList}>
                                    {suggestedQueries.map((q, i) => (
                                        <Box key={`${i}-${q.slice(0, 24)}`} className={classes.suggestedQueryItem}>
                                            <Text size="xs" className={classes.suggestedQueryText}>{q}</Text>
                                        </Box>
                                    ))}
                                </Box>
                            ) : (
                                <Text size="xs" c="dimmed" className={classes.suggestedQueriesEmpty}>
                                    통합 스키마 생성 또는 모델 로드 시 추천 질의문이 표시됩니다.
                                </Text>
                            )}
                        </Box>
                        )}
                    </Box>
                </Box>
                </Box>
            </Box>
            <Modal
                opened={dirtyModalOpen}
                onClose={closeDirtyModal}
                title="모델 저장 안내"
                centered
            >
                <Text size="sm">{DIRTY_MODAL_MESSAGE}</Text>
                <Group justify="flex-end" mt="md">
                    <Button size="xs" onClick={closeDirtyModal}>확인</Button>
                </Group>
            </Modal>
        </DefaultAppPageLayout>
    );
}
