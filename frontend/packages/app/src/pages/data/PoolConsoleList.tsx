import { ActionIcon, Badge, Box, Text } from "@mantine/core";
import type { CSSProperties } from "react";
import {
    IconDatabase,
    IconFileSpreadsheet,
    IconTool,
    IconX,
} from "@tabler/icons-react";
import type { PoolItem } from "@/libs/stores/dataManagement/types";
import { POOL_LIST_TITLE_MAX_LINES } from "@/libs/stores/dataManagement/constants";
import classes from "./datamanagement.module.css";

const TYPE_LABEL: Record<PoolItem["type"], string> = {
    file: "파일",
    tool: "도구",
    db: "DB",
};

const TYPE_BADGE_COLOR: Record<PoolItem["type"], string> = {
    file: "green",
    tool: "blue",
    db: "violet",
};

function PoolTypeIcon({ type }: { type: PoolItem["type"] }) {
    if (type === "file") return <IconFileSpreadsheet size={14} color="#16a34a" />;
    if (type === "tool") return <IconTool size={14} color="#3b82f6" />;
    return <IconDatabase size={14} color="#7c3aed" />;
}

function resolvePoolItemMeta(item: PoolItem): string {
    if (item.type === "file") {
        const sheet = item.sealed.hierarchy.sheets.find(
            s => s.id === item.sealed.hierarchy.activeSheetId,
        );
        const colCount = sheet?.columns.filter(c => c.selected).length ?? 0;
        return `${colCount}개 컬럼 선택 · ${sheet?.name ?? "시트"}`;
    }
    if (item.type === "tool") {
        return `도구 등록 ID · ${item.sealed.toolId}`;
    }
    const { host, dbName, tableName } = item.sealed;
    return `${dbName} · ${tableName} @ ${host}`;
}

type PoolConsoleListProps = {
    items: PoolItem[];
    activePoolId?: string | null;
    onItemClick?: (poolId: string) => void;
    onRemove?: (poolId: string) => void;
};

export function PoolConsoleList({
    items,
    activePoolId = null,
    onItemClick,
    onRemove,
}: PoolConsoleListProps) {
    return (
        <Box
            className={classes.poolItemsContainer}
            style={{ "--pool-list-title-max-lines": POOL_LIST_TITLE_MAX_LINES } as CSSProperties}
        >
            <Box className={classes.poolListHeader}>
                <Text size="10px" fw={700} className={classes.poolListHeaderLabel}>
                    적재된 원천 에셋
                </Text>
                <Badge size="xs" variant="light" color="gray" radius="sm">
                    {items.length}건
                </Badge>
            </Box>
            <Box className={classes.poolListBody}>
                {items.map((item, index) => {
                    const isActive = activePoolId === item.poolId;
                    return (
                        <Box
                            key={item.poolId}
                            className={`${classes.poolListItem} ${isActive ? classes.poolListItemActive : ""}`}
                            onClick={() => onItemClick?.(item.poolId)}
                            style={{ cursor: "pointer" }}
                        >
                            <span className={classes.poolListIndex}>{index + 1}</span>
                            <Box className={classes.poolListIcon}>
                                <PoolTypeIcon type={item.type} />
                            </Box>
                            <Box className={classes.poolListContent}>
                                <span className={classes.poolListName} title={item.displayName}>
                                    {item.displayName}
                                </span>
                                <Box className={classes.poolListMetaRow}>
                                    <span className={classes.poolListMeta}>
                                        {resolvePoolItemMeta(item)}
                                    </span>
                                    <Badge
                                        size="xs"
                                        variant="light"
                                        color={TYPE_BADGE_COLOR[item.type]}
                                        radius="sm"
                                        className={classes.poolListTypeBadge}
                                    >
                                        {TYPE_LABEL[item.type]}
                                    </Badge>
                                </Box>
                            </Box>
                            {onRemove && (
                                <ActionIcon
                                    size="sm"
                                    variant="subtle"
                                    color="gray"
                                    className={classes.poolListRemoveBtn}
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        onRemove(item.poolId);
                                    }}
                                >
                                    <IconX size={12} />
                                </ActionIcon>
                            )}
                        </Box>
                    );
                })}
            </Box>
        </Box>
    );
}
