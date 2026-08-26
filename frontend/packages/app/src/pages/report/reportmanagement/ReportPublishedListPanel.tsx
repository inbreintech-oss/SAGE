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
import type { SageData } from "@/features/data";
import type { ReportListItem } from "@/features/report-management";
import dataClasses from "../../data/datamanagement.module.css";
import classes from "./reportmanagement.module.css";

const EMPTY_MESSAGE = "배포된 보고서 목록을 불러오지 못했습니다";
const SEARCH_PLACEHOLDER = "보고서 검색...";

const FIELD_CONTROL_STYLES = {
    input: {
        fontSize: 12,
        fontWeight: 400,
        fontFamily: '"Noto Sans KR", sans-serif',
        color: "#333333",
    },
} as const;

function resolveAnalysisModelName(did: string | undefined, models: SageData[]): string {
    if (!did) return "연결된 분석모델 없음";
    const found = models.find(m => m.did === did);
    return found?.name ?? "알 수 없는 분석모델";
}

function resolveListTitle(item: ReportListItem): string {
    return item.description?.trim() || item.title?.trim() || "제목 없음";
}

export type ReportPublishedListPanelProps = {
    items: ReportListItem[];
    models: SageData[];
    isLoading: boolean;
    isError: boolean;
    selectedRid: string | null;
    hidden?: boolean;
    onSelect: (item: ReportListItem) => void;
    onCreateNew: () => void;
    onReload: () => void;
    onCollapse?: () => void;
};

export const ReportPublishedListPanel = memo(function ReportPublishedListPanel({
    items,
    models,
    isLoading,
    isError,
    selectedRid,
    hidden = false,
    onSelect,
    onCreateNew,
    onReload,
    onCollapse,
}: ReportPublishedListPanelProps) {
    const [searchRaw, setSearchRaw] = useState("");

    const filtered = useMemo(() => {
        const q = searchRaw.trim().toLowerCase();
        if (!q) return items;
        return items.filter(item => {
            const modelName = resolveAnalysisModelName(item.did, models).toLowerCase();
            return resolveListTitle(item).toLowerCase().includes(q)
                || modelName.includes(q)
                || (item.query ?? "").toLowerCase().includes(q);
        });
    }, [items, models, searchRaw]);

    return (
        <Box className={`${dataClasses.leftPanel} ${hidden ? dataClasses.leftPanelCollapsed : ""}`}>
            <Box className={dataClasses.panelHeader}>
                <Group gap={6} style={{ flex: 1, minWidth: 0 }}>
                    {onCollapse && (
                        <button
                            type="button"
                            className={dataClasses.collapseBtn}
                            title="목록 접기"
                            onClick={onCollapse}
                        >
                            <IconChevronsLeft size={14} />
                        </button>
                    )}
                    <Text className={dataClasses.panelHeaderTitle}>배포 보고서 목록</Text>
                    {filtered.length > 0 && (
                        <Box className={dataClasses.panelCountBadge}>
                            <Text size="10px" fw={700} c="white">{filtered.length}</Text>
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
                    신규 보고서
                </Button>
            </Box>

            <Box className={dataClasses.searchBar}>
                <Text className={dataClasses.fieldLabel}>보고서 검색</Text>
                <TextInput
                    size="xs"
                    className={dataClasses.placeholderInput}
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
                            <IconAlertCircle size={24} className={dataClasses.emptyPlaceholderIcon} />
                            <Text className={dataClasses.emptyPlaceholderText}>{EMPTY_MESSAGE}</Text>
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
                <Box className={dataClasses.emptyPlaceholderCard}>
                    <IconAlertCircle size={24} className={dataClasses.emptyPlaceholderIcon} />
                    <Text className={dataClasses.emptyPlaceholderText}>{EMPTY_MESSAGE}</Text>
                </Box>
            ) : filtered.length === 0 ? (
                <Box py="xl">
                    <Center>
                        <Text size="xs" className={dataClasses.emptyGuideText}>
                            검색 결과가 없습니다
                        </Text>
                    </Center>
                </Box>
            ) : (
                <Box>
                    {filtered.map(item => {
                        const isActive = item.rid === selectedRid;
                        const modelName = resolveAnalysisModelName(item.did, models);
                        return (
                            <Box
                                key={item.rid}
                                className={isActive ? dataClasses.dataListItemActive : dataClasses.dataListItem}
                                onClick={() => onSelect(item)}
                            >
                                <Group justify="space-between" wrap="nowrap" mb={3} gap={6}>
                                    <div className={dataClasses.dataItemTitle}>
                                        {resolveListTitle(item)}
                                    </div>
                                    {isActive && (
                                        <IconCheck size={14} color="#10B981" style={{ flexShrink: 0 }} />
                                    )}
                                </Group>
                                <div className={classes.reportListModelName}>
                                    {modelName}
                                </div>
                                <div className={dataClasses.dataItemDesc}>
                                    {item.query?.trim() || "등록된 설명이 없습니다."}
                                </div>
                            </Box>
                        );
                    })}
                </Box>
            )}
        </Box>
    );
});
