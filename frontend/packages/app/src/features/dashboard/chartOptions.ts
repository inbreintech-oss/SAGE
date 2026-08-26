import type { EChartsOption } from "echarts-for-react";
import type { CountEntry } from "./types";

const CHART_COLORS = ["#0090da", "#2563eb", "#3B82F6", "#60a5fa", "#94a3b8", "#64748b", "#cbd5e1"];

const BASE_TEXT = {
    fontFamily: '"Noto Sans KR", sans-serif',
    color: "#64748b",
    fontSize: 11,
};

function emptyChartOption(message: string): EChartsOption {
    return {
        title: {
            text: message,
            left: "center",
            top: "center",
            textStyle: { ...BASE_TEXT, fontSize: 13, color: "#94a3b8" },
        },
    };
}

export function buildDonutOption(entries: CountEntry[], title?: string): EChartsOption {
    if (entries.length === 0) return emptyChartOption("표시할 데이터가 없습니다");

    return {
        color: CHART_COLORS,
        tooltip: {
            trigger: "item",
            formatter: "{b}: {c} ({d}%)",
            textStyle: BASE_TEXT,
        },
        legend: {
            orient: "vertical",
            right: 0,
            top: "middle",
            textStyle: BASE_TEXT,
            itemWidth: 10,
            itemHeight: 10,
        },
        series: [
            {
                name: title ?? "",
                type: "pie",
                radius: ["42%", "68%"],
                center: ["38%", "50%"],
                avoidLabelOverlap: true,
                itemStyle: { borderRadius: 4, borderColor: "#fff", borderWidth: 2 },
                label: { show: false },
                data: entries.map(e => ({ name: e.label, value: e.value })),
            },
        ],
    };
}

export function buildHorizontalBarOption(entries: CountEntry[]): EChartsOption {
    if (entries.length === 0) return emptyChartOption("표시할 데이터가 없습니다");

    const reversed = [...entries].reverse();
    return {
        color: [CHART_COLORS[0]],
        grid: { left: 8, right: 24, top: 8, bottom: 8, containLabel: true },
        tooltip: {
            trigger: "axis",
            axisPointer: { type: "shadow" },
            textStyle: BASE_TEXT,
        },
        xAxis: {
            type: "value",
            axisLabel: BASE_TEXT,
            splitLine: { lineStyle: { color: "#e2e8f0" } },
        },
        yAxis: {
            type: "category",
            data: reversed.map(e => e.label),
            axisLabel: { ...BASE_TEXT, width: 80, overflow: "truncate" },
            axisTick: { show: false },
            axisLine: { show: false },
        },
        series: [
            {
                type: "bar",
                data: reversed.map(e => e.value),
                barMaxWidth: 18,
                itemStyle: { borderRadius: [0, 4, 4, 0] },
            },
        ],
    };
}

export function buildStackBarOption(entries: CountEntry[]): EChartsOption {
    if (entries.length === 0) return emptyChartOption("표시할 데이터가 없습니다");

    return {
        color: CHART_COLORS,
        grid: { left: 8, right: 8, top: 32, bottom: 8, containLabel: true },
        tooltip: {
            trigger: "axis",
            axisPointer: { type: "shadow" },
            textStyle: BASE_TEXT,
        },
        xAxis: {
            type: "category",
            data: entries.map(e => e.label),
            axisLabel: BASE_TEXT,
            axisTick: { show: false },
        },
        yAxis: {
            type: "value",
            axisLabel: BASE_TEXT,
            splitLine: { lineStyle: { color: "#e2e8f0" } },
        },
        series: [
            {
                type: "bar",
                data: entries.map(e => e.value),
                barMaxWidth: 40,
                itemStyle: { borderRadius: [4, 4, 0, 0] },
            },
        ],
    };
}

export function buildGaugeOption(mapped: number, total: number, ratio: number): EChartsOption {
    if (total === 0) return emptyChartOption("표시할 데이터가 없습니다");

    return {
        series: [
            {
                type: "gauge",
                startAngle: 200,
                endAngle: -20,
                min: 0,
                max: 100,
                splitNumber: 5,
                radius: "90%",
                center: ["50%", "58%"],
                axisLine: {
                    lineStyle: {
                        width: 14,
                        color: [[ratio / 100, "#0090da"], [1, "#e2e8f0"]],
                    },
                },
                pointer: { show: false },
                axisTick: { show: false },
                splitLine: { show: false },
                axisLabel: { show: false },
                detail: {
                    valueAnimation: true,
                    formatter: `{value}%\n${mapped}/${total}`,
                    fontSize: 22,
                    fontWeight: 700,
                    color: "#0090da",
                    offsetCenter: [0, "10%"],
                },
                data: [{ value: ratio }],
            },
        ],
    };
}
