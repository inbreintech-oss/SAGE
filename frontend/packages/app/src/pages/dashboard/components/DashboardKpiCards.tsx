import { memo } from "react";
import { Paper, SimpleGrid, Stack, Text } from "@mantine/core";
import {
    IconDatabase,
    IconFileAnalytics,
    IconTools,
} from "@tabler/icons-react";
import { useNavigate } from "react-router-dom";
import type { DashboardAggregates } from "@/features/dashboard";
import classes from "../dashboard.module.css";

type DashboardKpiCardsProps = {
    kpi: DashboardAggregates["kpi"];
};

const KPI_ITEMS = [
    {
        key: "models" as const,
        label: "생산된 모델",
        path: "/datamanagement",
        icon: IconDatabase,
        getValue: (kpi: DashboardAggregates["kpi"]) => String(kpi.modelCount),
        getSub: () => "통합 스키마 포함 (pangeaze)",
    },
    {
        key: "reports" as const,
        label: "생산된 보고서",
        path: "/report/reportlist",
        icon: IconFileAnalytics,
        getValue: (kpi: DashboardAggregates["kpi"]) => String(kpi.reportCount),
        getSub: () => null,
    },
    {
        key: "tools" as const,
        label: "생산된 도구",
        path: "/toolmanagement",
        icon: IconTools,
        getValue: (kpi: DashboardAggregates["kpi"]) => String(kpi.toolCount),
        getSub: () => null,
    },
];

export const DashboardKpiCards = memo(function DashboardKpiCards({ kpi }: DashboardKpiCardsProps) {
    const navigate = useNavigate();

    return (
        <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md">
            {KPI_ITEMS.map(item => {
                const Icon = item.icon;
                const sub = item.getSub(kpi);
                return (
                    <Paper
                        key={item.key}
                        withBorder
                        radius="md"
                        p="md"
                        className={classes.kpiCard}
                        onClick={() => navigate(item.path)}
                    >
                        <Stack gap={6}>
                            <Text className={classes.kpiLabel}>
                                <Icon size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />
                                {item.label}
                            </Text>
                            <Text className={classes.kpiValue}>{item.getValue(kpi)}</Text>
                            {sub && <Text className={classes.kpiSub}>{sub}</Text>}
                        </Stack>
                    </Paper>
                );
            })}
        </SimpleGrid>
    );
});
