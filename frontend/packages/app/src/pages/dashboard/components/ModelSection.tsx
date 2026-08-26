import { memo } from "react";
import { Button, SimpleGrid, Stack, Text } from "@mantine/core";
import { IconCopy, IconDatabase } from "@tabler/icons-react";
import { useNavigate } from "react-router-dom";
import { SagePaper } from "@/components";
import {
    buildDonutOption,
    buildGaugeOption,
    buildStackBarOption,
    formatSourceTypeCounts,
    type DashboardAggregates,
} from "@/features/dashboard";
import { useNotifications } from "@/hooks";
import { DashboardChart } from "./DashboardChart";
import classes from "../dashboard.module.css";

type ModelSectionProps = {
    aggregates: DashboardAggregates;
};

export const ModelSection = memo(function ModelSection({ aggregates }: ModelSectionProps) {
    const navigate = useNavigate();
    const { showSuccess, showError } = useNotifications();

    const sourceEntries = formatSourceTypeCounts(aggregates.sourceTypeCounts);

    const handleCopy = async (text: string) => {
        try {
            await navigator.clipboard.writeText(text);
            showSuccess("질의문이 클립보드에 복사되었습니다.");
        } catch {
            showError("복사에 실패했습니다.");
        }
    };

    return (
        <SagePaper withBorder radius="md">
            <SagePaper.Content title="데이터 분석 모델" icon={<IconDatabase size={20} />}>
                <Stack gap="md">
                    <SimpleGrid cols={{ base: 1, md: 3 }} spacing="md">
                        <div className={classes.chartPanel}>
                            <Text className={classes.chartTitle}>카테고리 분포</Text>
                            <DashboardChart option={buildDonutOption(aggregates.modelCategories)} />
                        </div>
                        <div className={classes.chartPanel}>
                            <Text className={classes.chartTitle}>데이터 소스 구성 (건수)</Text>
                            <DashboardChart option={buildStackBarOption(sourceEntries)} />
                            <div className={classes.statMiniGrid}>
                                {sourceEntries.map(entry => (
                                    <div key={entry.label} className={classes.statMiniItem}>
                                        <div className={classes.statMiniValue}>{entry.value}</div>
                                        <div className={classes.statMiniLabel}>{entry.label}</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                        <div className={classes.chartPanel}>
                            <Text className={classes.chartTitle}>통합 스키마 표준 매핑</Text>
                            <Text className={classes.chartHint}>
                                completed 모델 중 스키마 정상 보유 비율 (100% 미만 시 데이터 이상)
                            </Text>
                            <DashboardChart
                                option={buildGaugeOption(
                                    aggregates.schemaMapping.mapped,
                                    aggregates.schemaMapping.total,
                                    aggregates.schemaMapping.ratio,
                                )}
                            />
                        </div>
                    </SimpleGrid>

                    <Stack gap="xs">
                        <Text className={classes.chartTitle}>최근 생산 모델 (5건)</Text>
                        {aggregates.recentModels.length === 0 ? (
                            <Text className={classes.emptyText}>생산된 모델이 없습니다.</Text>
                        ) : (
                            <div style={{ overflowX: "auto" }}>
                                <table className={classes.dataTable}>
                                    <thead>
                                        <tr>
                                            <th>모델명</th>
                                            <th>카테고리</th>
                                            <th>소스</th>
                                            <th>스키마</th>
                                            <th>추천 질의</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {aggregates.recentModels.map(row => (
                                            <tr key={row.did}>
                                                <td>{row.name}</td>
                                                <td>{row.category}</td>
                                                <td>{row.sourceSummary}</td>
                                                <td>
                                                    {row.hasSchema ? (
                                                        <span className={classes.badgeOk}>매핑</span>
                                                    ) : (
                                                        <span className={classes.badgeMuted}>미매핑</span>
                                                    )}
                                                </td>
                                                <td>{row.suggestedQueryCount}건</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </Stack>

                    <Stack gap="xs">
                        <Text className={classes.chartTitle}>분석 가이드 — 추천 질의문</Text>
                        {aggregates.recommendedQueries.length === 0 ? (
                            <Text className={classes.emptyText}>추천 질의문이 없습니다.</Text>
                        ) : (
                            <div className={classes.queryScroll}>
                                {aggregates.recommendedQueries.map((item, index) => (
                                    <div key={`${item.modelDid}-${index}`} className={classes.queryCard}>
                                        <Text className={classes.queryText}>{item.query}</Text>
                                        <Text className={classes.queryMeta}>출처: {item.modelName}</Text>
                                        <div className={classes.queryActions}>
                                            <Button
                                                size="compact-xs"
                                                variant="light"
                                                leftSection={<IconCopy size={12} />}
                                                onClick={() => void handleCopy(item.query)}
                                            >
                                                복사
                                            </Button>
                                            <Button
                                                size="compact-xs"
                                                variant="subtle"
                                                onClick={() => navigate("/datamanagement")}
                                            >
                                                모델로 이동
                                            </Button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </Stack>
                </Stack>
            </SagePaper.Content>
        </SagePaper>
    );
});
