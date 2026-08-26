import {
    Alert,
    Button,
    Center,
    Loader,
    SimpleGrid,
    Stack,
} from "@mantine/core";
import { IconAlertCircle, IconLayoutDashboard, IconRefresh } from "@tabler/icons-react";
import { DefaultAppPageLayout } from "@/layouts/appPage";
import { useDashboardData } from "@/features/dashboard";
import { DashboardKpiCards } from "./dashboard/components/DashboardKpiCards";
import { ModelSection } from "./dashboard/components/ModelSection";
import { ReportSection } from "./dashboard/components/ReportSection";
import { ToolSection } from "./dashboard/components/ToolSection";
import classes from "./dashboard/dashboard.module.css";

function formatTimestamp(date: Date): string {
    return date.toLocaleString("ko-KR", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
    });
}

export default function DashboardPage() {
    const { aggregates, isLoading, isError, hasFetched, refetch } = useDashboardData();

    const lastUpdated = formatTimestamp(new Date());

    const statusBar = (
        <div className={classes.pageStatusBar}>
            <span className={classes.pageStatusTimestamp}>최종 갱신: {lastUpdated}</span>
            <span style={{ display: "flex", alignItems: "center" }}>
                <span className={classes.pipelineStatusDot} />
                <span className={classes.pipelineStatusText}>시스템 정상</span>
            </span>
            <Button
                size="compact-xs"
                variant="subtle"
                leftSection={<IconRefresh size={14} />}
                onClick={refetch}
                loading={isLoading}
            >
                새로고침
            </Button>
        </div>
    );

    return (
        <DefaultAppPageLayout icon={<IconLayoutDashboard size={24} />} buttons={statusBar}>
            <Stack gap="md" w="100%">
                {isError && (
                    <Alert
                        icon={<IconAlertCircle size={16} />}
                        color="blue"
                        variant="light"
                        title="일부 데이터를 불러오지 못했습니다"
                    >
                        목록 API 조회에 실패했습니다. 새로고침을 시도해 주세요.
                    </Alert>
                )}

                {isLoading && !hasFetched ? (
                    <Center py="xl">
                        <Loader color="sageBlue" />
                    </Center>
                ) : (
                    <>
                        <DashboardKpiCards kpi={aggregates.kpi} />
                        <ModelSection aggregates={aggregates} />
                        <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="md">
                            <ReportSection aggregates={aggregates} />
                            <ToolSection aggregates={aggregates} />
                        </SimpleGrid>
                    </>
                )}
            </Stack>
        </DefaultAppPageLayout>
    );
}
