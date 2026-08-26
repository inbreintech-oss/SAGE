import {Box, Center, Table} from "@mantine/core";
import {useVegaEmbed} from "react-vega";
import {useSageMarkdownData} from "../SageMarkdownDataContext";
import type {VisualizationSpec} from "vega-embed";
import {useEffect, useRef} from "react";
import ECharts, {type EChartsOption} from "echarts-for-react";

type TableRow = Record<string, unknown>;

type SagePlaceholderTableProps = {
    data: TableRow[]
};

function SagePlaceholderTable({
    data
}: SagePlaceholderTableProps) {
    if (data.length === 0) return null;

    const columns = Object.keys(data[0]);

    return (
        <Table.ScrollContainer minWidth={300} my="md">
            <Table>
                <Table.Thead>
                    <Table.Tr>
                        {columns.map(col => (
                            <Table.Th key={col} bg="gray.1">{col}</Table.Th>
                        ))}
                    </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                    {data.map((row, i) => (
                        <Table.Tr key={i}>
                            {columns.map(col => (
                                <Table.Td key={col}>{String(row[col] ?? "")}</Table.Td>
                            ))}
                        </Table.Tr>
                    ))}
                </Table.Tbody>
            </Table>
        </Table.ScrollContainer>
    );
}

type SagePlaceholderVegaProps = {
    spec: VisualizationSpec
};

function SagePlaceholderVega({
    spec
}: SagePlaceholderVegaProps) {
    const ref = useRef<HTMLDivElement>(null);
    const embed = useVegaEmbed({
        ref: ref,
        spec: {
            ...spec,
            // @ts-expect-error react-vega에 width: container 타입이 존재하지 않음.
            "width": "container",
            // @ts-expect-error react-vega에 height: container 타입이 존재하지 않음.
            "height": "container",
            "autosize": {"type": "fit", "resize": true},
        },
        options: {
            mode: "vega-lite",
        }
    });

    useEffect(() => {
        if (!ref.current || !embed) return;
        const observer = new ResizeObserver(() => {
            window.dispatchEvent(new Event("resize"));
            embed?.view.runAsync();
        });

        observer.observe(ref.current);
        return () => {
            observer.disconnect();
        };
    }, [embed]);

    return (
        <Center my="md">
            <Box ref={ref} w="100%" h={350} maw={500}/>
        </Center>
    );
}

type SagePlaceholderEchartsProps = {
    option: EChartsOption;
}

function SagePlaceholderEcharts({
    option,
}: SagePlaceholderEchartsProps) {
    return (
        <ECharts option={option}
                 opts={{
                     renderer: "canvas",
                 }}
        />
    )
}

export type PlaceholderHandlerProps = {
    id: string;
}

export default function PlaceholderHandler({
    id
}: PlaceholderHandlerProps) {
    const data = useSageMarkdownData();
    const placeholderData = data[id];

    if (placeholderData === undefined || placeholderData === null) return null;

    switch (placeholderData.type) {
        case "table":
            return <SagePlaceholderTable data={placeholderData.value as TableRow[]}/>;
        case "vega-lite":
            return <SagePlaceholderVega spec={placeholderData.value as VisualizationSpec}/>;
        case "echarts":
            return <SagePlaceholderEcharts option={placeholderData.value as EChartsOption}/>;
        default:
            return null;
    }
}
