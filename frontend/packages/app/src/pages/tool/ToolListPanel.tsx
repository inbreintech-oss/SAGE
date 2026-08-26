import { memo, useMemo, useState } from "react";
import {
    Box,
    Button,
    Center,
    Group,
    Loader,
    Stack,
    Text,
    TextInput,
} from "@mantine/core";
import {
    IconAlertCircle,
    IconChevronsLeft,
    IconPlus,
    IconRefresh,
    IconSearch,
} from "@tabler/icons-react";
import { resolveDisplayKeywords } from "@/features/tool-management/normalizeTool";
import { CopyableListItemId } from "@/components/copyableListItemId";
import {
    EMPTY_LIST_MESSAGE,
    LIST_LOAD_ERROR_MESSAGE,
    SEARCH_PLACEHOLDER,
    getCategoryLabel,
} from "@/libs/stores/toolManagement/constants";
import { filterToolsByQuery, parseOrTokens } from "@/libs/stores/toolManagement/searchSlice";
import type { ToolListItem } from "@/libs/stores/toolManagement/types";
import classes from "./toolmanagement.module.css";

const FIELD_CONTROL_STYLES = {
    input: {
        fontSize: 12,
        fontWeight: 400,
        fontFamily: '"Noto Sans KR", sans-serif',
        color: "#333333",
    },
} as const;

export type ToolListPanelProps = {
    tools: ToolListItem[];
    listStatus: "idle" | "loading" | "success" | "error";
    selectedToolId: string | null;
    collapsed?: boolean;
    onSelectTool: (tool: ToolListItem) => void;
    onCreateNew: () => void;
    onReload: () => void;
    onCollapse: () => void;
};

/**
 * 좌측 도구 목록 — 검색어는 로컬 state 로만 관리하여
 * 입력 시 전체 ToolManagementPage 가 리렌더·크래시 되지 않도록 격리합니다.
 */
export const ToolListPanel = memo(function ToolListPanel({
    tools,
    listStatus,
    selectedToolId,
    collapsed = false,
    onSelectTool,
    onCreateNew,
    onReload,
    onCollapse,
}: ToolListPanelProps) {
    const [searchRaw, setSearchRaw] = useState("");

    const filteredTools = useMemo(
        () => filterToolsByQuery(tools, {
            raw: searchRaw,
            orTokens: parseOrTokens(searchRaw),
        }),
        [tools, searchRaw],
    );

    const listEmptyState = useMemo(() => {
        if (tools.length === 0) return "no-data" as const;
        if (filteredTools.length === 0) return "no-match" as const;
        return "none" as const;
    }, [tools.length, filteredTools.length]);

    return (
        <Box className={`${classes.leftPanel} ${collapsed ? classes.leftPanelCollapsed : ""}`}>
            <Box className={classes.panelHeader}>
                <Group gap={6}>
                    <button
                        type="button"
                        className={classes.collapseBtn}
                        title="목록 접기"
                        onClick={onCollapse}
                    >
                        <IconChevronsLeft size={14} />
                    </button>
                    <Text className={classes.panelHeaderTitle}>등록된 도구 목록</Text>
                    {filteredTools.length > 0 && (
                        <Box style={{
                            minWidth: 18, height: 18, borderRadius: 9,
                            background: "#2563eb", display: "flex",
                            alignItems: "center", justifyContent: "center",
                        }}>
                            <Text fz={10} fw={700} c="white">
                                {filteredTools.length}
                            </Text>
                        </Box>
                    )}
                </Group>
                <Button
                    size="xs"
                    color="blue"
                    leftSection={<IconPlus size={11} />}
                    onClick={onCreateNew}
                    styles={{ label: { fontSize: "10px", fontWeight: 700 } }}
                >
                    신규 도구
                </Button>
            </Box>

            <Box className={classes.searchBar}>
                <Text className={classes.fieldLabel}>도구 검색 (Search &amp; Filter)</Text>
                <TextInput
                    className={`${classes.placeholderInput} ${classes.formFieldInput}`}
                    size="xs"
                    placeholder={SEARCH_PLACEHOLDER}
                    leftSection={<IconSearch size={13} />}
                    value={searchRaw}
                    onChange={e => setSearchRaw(e.currentTarget.value)}
                    styles={FIELD_CONTROL_STYLES}
                />
            </Box>

            {listStatus === "loading" ? (
                <Center py="xl"><Loader size="sm" color="blue" /></Center>
            ) : listStatus === "error" ? (
                <Box py="xl">
                    <Center>
                        <Stack align="center" gap="xs">
                            <IconAlertCircle size={24} className={classes.emptyPlaceholderIcon} />
                            <Text className={classes.emptyPlaceholderText}>
                                {LIST_LOAD_ERROR_MESSAGE}
                            </Text>
                            <Button
                                size="xs"
                                variant="light"
                                leftSection={<IconRefresh size={12} />}
                                onClick={onReload}
                            >
                                다시조회
                            </Button>
                        </Stack>
                    </Center>
                </Box>
            ) : listEmptyState === "no-data" ? (
                <Box className={classes.emptyPlaceholderCard}>
                    <IconAlertCircle size={24} className={classes.emptyPlaceholderIcon} />
                    <Text className={classes.emptyPlaceholderText}>
                        {EMPTY_LIST_MESSAGE}
                    </Text>
                </Box>
            ) : listEmptyState === "no-match" ? (
                <Box py="xl">
                    <Center>
                        <Text size="xs" c="dimmed">일치하는 도구가 없습니다.</Text>
                    </Center>
                </Box>
            ) : (
                <Box className={classes.listScroll}>
                    {filteredTools.map(tool => {
                        const toolId = tool?.tool_id ?? "";
                        const isActive = selectedToolId === toolId;
                        const keywords = resolveDisplayKeywords(tool);

                        return (
                            <Box
                                key={toolId || tool.title}
                                className={isActive ? classes.toolListItemActive : classes.toolListItem}
                                onClick={() => onSelectTool(tool)}
                            >
                                <Group justify="space-between" wrap="nowrap" className={classes.toolItemTitleRow}>
                                    <span className={classes.toolItemTitle}>{tool.title ?? ""}</span>
                                    <span className={
                                        isActive
                                            ? classes.categoryBadgeActive
                                            : classes.categoryBadgeDefault
                                    }>
                                        {getCategoryLabel(tool.category ?? "")}
                                    </span>
                                </Group>
                                <CopyableListItemId
                                    label="도구 등록 ID"
                                    value={toolId}
                                    copiedMessage="도구 등록 ID가 복사되었습니다."
                                    trailing={(
                                        <span className={
                                            tool.status === "assetized"
                                                ? classes.statusBadgeAssetized
                                                : classes.statusBadgeGenerated
                                        }>
                                            {tool.status === "assetized" ? "자산등록" : "생성등록"}
                                        </span>
                                    )}
                                />
                                <Text className={classes.toolItemDesc}>
                                    {tool.description || "등록된 설명이 없습니다."}
                                </Text>
                                <div className={classes.keywordTagsRow}>
                                    {keywords.map((kw, idx) => (
                                        <span
                                            key={`${toolId}-${kw}-${idx}`}
                                            className={classes.keywordBadge}
                                        >
                                            {kw}
                                        </span>
                                    ))}
                                </div>
                            </Box>
                        );
                    })}
                </Box>
            )}
        </Box>
    );
});

export default ToolListPanel;
