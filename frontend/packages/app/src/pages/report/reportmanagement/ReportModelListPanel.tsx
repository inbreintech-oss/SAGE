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
    IconRefresh,
    IconSearch,
} from "@tabler/icons-react";
import type { SageData } from "@/features/data";
import { CopyableListItemId } from "@/components/copyableListItemId";
import classes from "./reportmanagement.module.css";

const EMPTY_LIST_MESSAGE = "데이터 분석 모델 목록을 불러오지 못했습니다";

export type ReportModelListPanelProps = {
    items: SageData[];
    isLoading: boolean;
    isError: boolean;
    selectedDid: string | null;
    collapsed?: boolean;
    onSelect: (item: SageData) => void;
    onReload: () => void;
    onCollapse: () => void;
};

export const ReportModelListPanel = memo(function ReportModelListPanel({
    items,
    isLoading,
    isError,
    selectedDid,
    collapsed = false,
    onSelect,
    onReload,
    onCollapse,
}: ReportModelListPanelProps) {
    const [searchRaw, setSearchRaw] = useState("");

    const filteredItems = useMemo(() => {
        const q = searchRaw.trim().toLowerCase();
        if (!q) return items;
        return items.filter(
            d => d.name.toLowerCase().includes(q)
                || (d.description ?? "").toLowerCase().includes(q),
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
                    <Text className={classes.panelHeaderTitle}>데이터 분석 모델</Text>
                    {filteredItems.length > 0 && (
                        <Box className={classes.panelCountBadge}>
                            <Text size="10px" fw={700} c="white">{filteredItems.length}</Text>
                        </Box>
                    )}
                </Group>
                <Button
                    size="compact-xs"
                    variant="subtle"
                    color="gray"
                    leftSection={<IconRefresh size={12} />}
                    onClick={onReload}
                >
                    새로고침
                </Button>
            </Box>

            {!collapsed && (
                <>
                    <Box className={classes.searchBar}>
                        <Text className={classes.fieldLabel}>분석명 검색</Text>
                        <TextInput
                            size="xs"
                            placeholder="모델명·설명 검색"
                            leftSection={<IconSearch size={14} />}
                            value={searchRaw}
                            onChange={e => setSearchRaw(e.currentTarget.value)}
                        />
                    </Box>

                    <Box className={classes.listBody}>
                        {isLoading ? (
                            <Center py="xl">
                                <Loader size="sm" />
                            </Center>
                        ) : isError ? (
                            <Box className={classes.emptyPlaceholderCard}>
                                <IconAlertCircle size={24} className={classes.emptyPlaceholderIcon} />
                                <Text className={classes.emptyPlaceholderText}>{EMPTY_LIST_MESSAGE}</Text>
                            </Box>
                        ) : filteredItems.length === 0 ? (
                            <Box className={classes.emptyPlaceholderCard}>
                                <Text size="xs" c="dimmed" ta="center">
                                    {searchRaw.trim() ? "검색 결과가 없습니다." : "등록된 분석 모델이 없습니다."}
                                </Text>
                            </Box>
                        ) : (
                            <Stack gap={0}>
                                {filteredItems.map(item => {
                                    const active = item.did === selectedDid;
                                    const queryCount = item.suggested_queries?.length ?? 0;
                                    return (
                                        <button
                                            key={item.did}
                                            type="button"
                                            className={`${classes.listItem} ${active ? classes.listItemActive : ""}`}
                                            onClick={() => onSelect(item)}
                                        >
                                            <Text className={classes.listItemTitle} lineClamp={1}>
                                                {item.name}
                                            </Text>
                                            <Text className={classes.listItemDesc} lineClamp={2}>
                                                {item.description || "설명 없음"}
                                            </Text>
                                            <Group gap={8} mt={6} justify="space-between" wrap="nowrap">
                                                <CopyableListItemId
                                                    label="데이터 모델 등록 ID"
                                                    value={item.did}
                                                    copiedMessage="데이터 모델 등록 ID가 복사되었습니다."
                                                />
                                                {queryCount > 0 && (
                                                    <Text size="10px" c="dimmed" style={{ flexShrink: 0 }}>
                                                        추천질의 {queryCount}
                                                    </Text>
                                                )}
                                            </Group>
                                        </button>
                                    );
                                })}
                            </Stack>
                        )}
                    </Box>
                </>
            )}
        </Box>
    );
});
