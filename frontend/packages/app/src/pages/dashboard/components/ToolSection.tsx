import { memo } from "react";
import { Stack, Text } from "@mantine/core";
import { IconTools } from "@tabler/icons-react";
import { SagePaper } from "@/components";
import {
    buildDonutOption,
    buildHorizontalBarOption,
    buildStackBarOption,
    type DashboardAggregates,
} from "@/features/dashboard";
import { DashboardChart } from "./DashboardChart";
import classes from "../dashboard.module.css";

type ToolSectionProps = {
    aggregates: DashboardAggregates;
};

export const ToolSection = memo(function ToolSection({ aggregates }: ToolSectionProps) {
    return (
        <SagePaper withBorder radius="md" h="100%">
            <SagePaper.Content title="도구" icon={<IconTools size={20} />}>
                <Stack gap="md">
                    <div className={classes.chartPanel}>
                        <Text className={classes.chartTitle}>카테고리 분포</Text>
                        <DashboardChart option={buildDonutOption(aggregates.toolCategories)} />
                    </div>

                    <div className={classes.chartPanel}>
                        <Text className={classes.chartTitle}>연계기관별 도구</Text>
                        <DashboardChart option={buildHorizontalBarOption(aggregates.toolProviders)} />
                    </div>

                    <div className={classes.chartPanel}>
                        <Text className={classes.chartTitle}>생산 상태별 도구</Text>
                        <DashboardChart option={buildStackBarOption(aggregates.toolStatusCounts)} height={180} />
                    </div>

                    <Stack gap="xs">
                        <Text className={classes.chartTitle}>연관 키워드 Top 10</Text>
                        {aggregates.toolTags.length === 0 ? (
                            <Text className={classes.emptyText}>연관 키워드가 없습니다.</Text>
                        ) : (
                            <div className={classes.tagList}>
                                {aggregates.toolTags.map(tag => (
                                    <span key={tag.label} className={classes.tagChip}>
                                        {tag.label}
                                        <span style={{ marginLeft: 4, opacity: 0.7 }}>({tag.value})</span>
                                    </span>
                                ))}
                            </div>
                        )}
                    </Stack>
                </Stack>
            </SagePaper.Content>
        </SagePaper>
    );
});
