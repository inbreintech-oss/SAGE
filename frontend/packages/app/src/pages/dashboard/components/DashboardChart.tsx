import { memo } from "react";
import ECharts, { type EChartsOption } from "echarts-for-react";
import { Box } from "@mantine/core";

type DashboardChartProps = {
    option: EChartsOption;
    height?: number;
};

export const DashboardChart = memo(function DashboardChart({
    option,
    height = 220,
}: DashboardChartProps) {
    return (
        <Box style={{ height, width: "100%" }}>
            <ECharts
                option={option}
                style={{ height: "100%", width: "100%" }}
                opts={{ renderer: "svg" }}
                notMerge
                lazyUpdate
            />
        </Box>
    );
});
