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
    IconCheck,
    IconChevronsLeft,
    IconPlus,
    IconRefresh,
    IconSearch,
} from "@tabler/icons-react";
import type { SageData, DataSource } from "@/features/data";
import { resolveToolDisplayName, isToolDataSource, resolveToolSourceId } from "@/libs/stores/dataManagement/poolSlice";
import { CopyableListItemId } from "@/components/copyableListItemId";
import { getCategoryLabel, resolveCategoryCode } from "@/libs/stores/toolManagement/commonCodes";
import { EMPTY_LIST_MESSAGE, SEARCH_PLACEHOLDER } from "@/libs/stores/dataManagement/constants";
import classes from "./datamanagement.module.css";

const FIELD_CONTROL_STYLES = {
    input: {
        fontSize: 12,
        fontWeight: 400,
        fontFamily: '"Noto Sans KR", sans-serif',
        color: "#333333",
    },
} as const;

function getFirstFileName(sources?: DataSource[]): string | null {
    const src = sources?.find(s => s.type === "file");
    if (!src) return null;
    return src.path.split("/").pop() ?? src.path;
}

function getFirstToolName(
    sources?: DataSource[],
    toolTitleById?: Record<string, string>,
): string | null {
    const src = sources?.find(isToolDataSource);
    if (!src) return null;
    const toolId = resolveToolSourceId(src);
    if (!toolId) return null;
    return resolveToolDisplayName(toolId, src.origin, toolTitleById);
}

export type DataListPanelProps = {
    items: SageData[];
    isLoading: boolean;
    isError: boolean;
    selectedDid: string | null;
    toolTitleById?: Record<string, string>;
    collapsed?: boolean;
    onSelect: (item: SageData) => void;
    onCreateNew: () => void;
    onReload: () => void;
    onCollapse: () => void;
};

export const DataListPanel = memo(function DataListPanel({
    items,
    isLoading,
    isError,
    selectedDid,
    toolTitleById,
    collapsed = false,
    onSelect,
    onCreateNew,
    onReload,
    onCollapse,
}: DataListPanelProps) {
    const [searchRaw, setSearchRaw] = useState("");

    const filteredItems = useMemo(() => {
        const q = searchRaw.trim().toLowerCase();
        if (!q) return items;
        return items.filter(
            d => d.name.toLowerCase().includes(q) ||
                (d.description ?? "").toLowerCase().includes(q),
        );
    }, [items, searchRaw]);

    return (
        <Box className={`${classes.leftPanel} ${collapsed ? classes.leftPanelCollapsed : ""}`}>
            <Box className={classes.panelHeader}>
                <Group gap={6} style={{ flex: 1, minWidth: 0 }}>
                    <button
                        type="button"
                        className={classes.collapseBtn}
                        title="목록 접기"
                        onClick={onCollapse}
                    >
                        <IconChevronsLeft size={14} />
                    </button>
                    <Text className={classes.panelHeaderTitle}>데이터 분석 모델 목록</Text>
                    {filteredItems.length > 0 && (
                        <Box className={classes.panelCountBadge}>
                            <Text size="10px" fw={700} c="white">{filteredItems.length}</Text>
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
                    신규 분석모델
                </Button>
            </Box>

            <Box className={classes.searchBar}>
                <Text className={classes.fieldLabel}>분석모델 검색</Text>
                <TextInput
                    size="xs"
                    className={classes.placeholderInput}
                    placeholder={SEARCH_PLACEHOLDER}
                    leftSection={<IconSearch size={13} />}
                    value={searchRaw}
                    onChange={e => setSearchRaw(e.currentTarget.value)}
                    styles={FIELD_CONTROL_STYLES}
                />
            </Box>

            {isLoading ? (
                <Center py="xl"><Loader size="sm" color="blue" /></Center>
            ) : isError ? (
                <Box py="xl">
                    <Center>
                        <Stack align="center" gap="xs">
                            <IconAlertCircle size={24} className={classes.emptyPlaceholderIcon} />
                            <Text className={classes.emptyPlaceholderText}>{EMPTY_LIST_MESSAGE}</Text>
                            <Button
                                size="xs"
                                variant="light"
                                leftSection={<IconRefresh size={12} />}
                                onClick={onReload}
                            >
                                다시 시도
                            </Button>
                        </Stack>
                    </Center>
                </Box>
            ) : items.length === 0 && !searchRaw.trim() ? (
                <Box className={classes.emptyPlaceholderCard}>
                    <IconAlertCircle size={24} className={classes.emptyPlaceholderIcon} />
                    <Text className={classes.emptyPlaceholderText}>{EMPTY_LIST_MESSAGE}</Text>
                </Box>
            ) : filteredItems.length === 0 ? (
                <Box py="xl">
                    <Center>
                        <Text size="xs" className={classes.emptyGuideText}>
                            검색 결과가 없습니다
                        </Text>
                    </Center>
                </Box>
            ) : (
                <Box>
                    {filteredItems.map(item => {
                        const fileName = getFirstFileName(item.sources);
                        const toolName = getFirstToolName(item.sources, toolTitleById);
                        const isActive = selectedDid === item.did;
                        const categoryCode = resolveCategoryCode(item.category);
                        return (
                            <Box
                                key={item.did}
                                className={isActive ? classes.dataListItemActive : classes.dataListItem}
                                onClick={() => onSelect(item)}
                            >
                                <Group justify="space-between" wrap="nowrap" mb={3} gap={6}>
                                    <div className={classes.dataItemTitle}>{item.name}</div>
                                    <Group gap={6} wrap="nowrap" style={{ flexShrink: 0 }}>
                                        <span className={
                                            isActive
                                                ? classes.categoryBadgeActive
                                                : classes.categoryBadgeDefault
                                        }>
                                            {getCategoryLabel(categoryCode)}
                                        </span>
                                        {isActive && (
                                            <IconCheck size={14} color="#10B981" />
                                        )}
                                    </Group>
                                </Group>
                                <CopyableListItemId
                                    label="데이터 모델 등록 ID"
                                    value={item.did}
                                    copiedMessage="데이터 모델 등록 ID가 복사되었습니다."
                                />
                                <div className={classes.dataItemDesc}>
                                    {item.description?.trim() || "등록된 설명이 없습니다."}
                                </div>
                                <div className={classes.sourceTagsRow}>
                                    {fileName && (
                                        <span className={classes.sourceTagFile}>{fileName}</span>
                                    )}
                                    {toolName && (
                                        <span className={classes.sourceTagTool}>{toolName}</span>
                                    )}
                                </div>
                            </Box>
                        );
                    })}
                </Box>
            )}
        </Box>
    );
});

export default DataListPanel;
