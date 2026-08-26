import { memo } from "react";
import { Stack, Text } from "@mantine/core";
import { IconFileAnalytics } from "@tabler/icons-react";
import { SagePaper } from "@/components";
import {
    buildDonutOption,
    buildHorizontalBarOption,
    buildStackBarOption,
    formatQueryTypeCounts,
    QUERY_TYPE_LABELS,
    type DashboardAggregates,
} from "@/features/dashboard";
import { DashboardChart } from "./DashboardChart";
import classes from "../dashboard.module.css";

type ReportSectionProps = {
    aggregates: DashboardAggregates;
};

export const ReportSection = memo(function ReportSection({ aggregates }: ReportSectionProps) {
    const queryTypeEntries = formatQueryTypeCounts(aggregates.reportQueryTypes);

    return (
        <SagePaper withBorder radius="md" h="100%">
            <SagePaper.Content title="보고서" icon={<IconFileAnalytics size={20} />}>
                <Stack gap="md">
                    <div className={classes.chartPanel}>
                        <Text className={classes.chartTitle}>활용 모델 Top 5</Text>
                        <DashboardChart option={buildHorizontalBarOption(aggregates.reportModelUsage)} />
                    </div>

                    <div className={classes.chartPanel}>
                        <Text className={classes.chartTitle}>질의 유형 (자동 분류)</Text>
                        <Text className={classes.chartHint}>
                            1차 휴리스틱: {QUERY_TYPE_LABELS.short} (&lt;50자) · {QUERY_TYPE_LABELS.exploratory} (50~150자) · {QUERY_TYPE_LABELS.detailed} (150자+)
                        </Text>
                        <DashboardChart option={buildDonutOption(queryTypeEntries)} height={200} />
                    </div>

                    <div className={classes.chartPanel}>
                        <Text className={classes.chartTitle}>자연어 질의 길이</Text>
                        <div className={classes.metricRow}>
                            <span className={classes.metricLabel}>평균 길이</span>
                            <span className={classes.metricValue}>
                                {aggregates.reportQueryLength.withQuery > 0
                                    ? `${aggregates.reportQueryLength.average}자`
                                    : "-"}
                            </span>
                        </div>
                        <div className={classes.metricRow}>
                            <span className={classes.metricLabel}>최소 / 최대</span>
                            <span className={classes.metricValue}>
                                {aggregates.reportQueryLength.withQuery > 0
                                    ? `${aggregates.reportQueryLength.min} / ${aggregates.reportQueryLength.max}자`
                                    : "-"}
                            </span>
                        </div>
                        <DashboardChart
                            option={buildStackBarOption(aggregates.reportQueryLength.buckets)}
                            height={160}
                        />
                    </div>

                    <Stack gap={4}>
                        <Text className={classes.chartTitle}>활용 도구 · 스키마 매핑</Text>
                        <div className={classes.metricRow}>
                            <span className={classes.metricLabel}>스키마 연계 보고서</span>
                            <span className={classes.metricValue}>{aggregates.reportSchemaLinkedCount}건</span>
                        </div>
                        {aggregates.reportToolUsage.length === 0 ? (
                            <Text className={classes.emptyText}>활용 도구 데이터가 없습니다.</Text>
                        ) : (
                            aggregates.reportToolUsage.map(item => (
                                <div key={item.label} className={classes.metricRow}>
                                    <span className={classes.metricLabel}>{item.label}</span>
                                    <span className={classes.metricValue}>{item.value}건</span>
                                </div>
                            ))
                        )}
                    </Stack>

                    <Stack gap="xs">
                        <Text className={classes.chartTitle}>최근 배포 보고서 (5건)</Text>
                        {aggregates.recentReports.length === 0 ? (
                            <Text className={classes.emptyText}>배포된 보고서가 없습니다.</Text>
                        ) : (
                            <div style={{ overflowX: "auto" }}>
                                <table className={classes.dataTable}>
                                    <thead>
                                        <tr>
                                            <th>제목</th>
                                            <th>활용 모델</th>
                                            <th>질의</th>
                                            <th>도구</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {aggregates.recentReports.map(row => (
                                            <tr key={row.rid}>
                                                <td>{row.title}</td>
                                                <td>{row.modelName}</td>
                                                <td>{row.queryPreview}</td>
                                                <td>{row.toolCount}건</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </Stack>
                </Stack>
            </SagePaper.Content>
        </SagePaper>
    );
});
