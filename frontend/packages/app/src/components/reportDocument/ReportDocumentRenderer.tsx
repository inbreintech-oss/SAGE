import type { CSSProperties, ReactNode } from "react";
import { Alert, Box, Grid, ScrollArea, Table, Text, Title } from "@mantine/core";
import ECharts from "echarts-for-react";
import { ReportMarkdown } from "./reportMarkdown";
import type {
    ReportBlockData,
    ReportBlockRole,
    ReportCardData,
    ReportDataStyle,
    ReportDocumentBody,
    ReportGenerateResult,
    ReportHeaderData,
    ReportKpiItem,
    ReportLayoutBlock,
    ReportTableData,
    ReportTableDtype,
} from "@/features/report-management";
import {
    applyReportChartTheme,
    isEchartBlockData,
    normalizeEchartPresentation,
    resolveReportChartHeight,
} from "@/features/report-management/echartUtils";
import {
    isCardData,
    isHeaderData,
    isTableData,
    resolveTableColumnSpecs,
} from "@/features/report-management/reportDocumentTypes";
import {
    isCardBlockType,
    isChartBlockType,
    isLayoutContainer,
    isTableBlockType,
    resolveHeaderType,
    resolvePayloadRole,
} from "@/features/report-management/reportBlockUtils";
import classes from "./reportDocument.module.css";

function typeClass(blockType: string): string {
    const map: Record<string, string | undefined> = {
        document_title: classes.typeDocumentTitle,
        section_title: classes.typeSectionTitle,
        summary_card: classes.typeSummaryCard,
        insight_card: classes.typeInsightCard,
        kpi_card: classes.typeKpiCard,
        text_card: classes.typeTextCard,
        closing_card: classes.typeClosingCard,
        metrics_table: classes.typeMetricsTable,
        appendix_table: classes.typeAppendixTable,
        primary_chart: classes.typePrimaryChart,
        secondary_chart: classes.typeSecondaryChart,
    };
    return map[blockType] ?? "";
}

function roleClass(role?: ReportBlockRole): string {
    if (!role) return "";
    const key = role.replace(/_/g, "-");
    const map: Record<string, string | undefined> = {
        "chart-insight": classes.roleChartInsight,
        "table-insight": classes.roleTableInsight,
        conclusions: classes.roleConclusions,
    };
    return map[key] ?? "";
}

function blockSurfaceClass(blockType: string, role?: ReportBlockRole): string {
    return `${typeClass(blockType)} ${roleClass(role)}`.trim();
}

function blockShellClass(blockType: string, role?: ReportBlockRole, dataStyle?: ReportDataStyle): string {
    return [
        classes.blockShell,
        blockSurfaceClass(blockType, role),
        resolveDataStyleClasses(dataStyle),
    ].filter(Boolean).join(" ");
}

function resolveDataStyleClasses(style?: ReportDataStyle): string {
    if (!style) return "";
    const parts: string[] = [];
    if (style.variant && style.variant !== "default") {
        parts.push(classes[`styleVariant${style.variant.charAt(0).toUpperCase()}${style.variant.slice(1)}` as keyof typeof classes] ?? "");
    }
    if (style.density) {
        const densityKey = `styleDensity${style.density.charAt(0).toUpperCase()}${style.density.slice(1)}` as keyof typeof classes;
        parts.push(classes[densityKey] ?? "");
    }
    if (style.accent) {
        parts.push(classes.styleAccent ?? "");
    }
    if (style.border === false) {
        parts.push(classes.styleNoBorder ?? "");
    }
    return parts.filter(Boolean).join(" ");
}

function extractDataStyle(payload: ReportBlockData | undefined): ReportDataStyle | undefined {
    if (!payload || typeof payload !== "object" || !("style" in payload)) return undefined;
    const style = (payload as { style?: ReportDataStyle }).style;
    return style && typeof style === "object" ? style : undefined;
}

function HeaderBlock({
    data,
    role,
    blockType,
}: {
    data: ReportHeaderData;
    role?: ReportBlockRole;
    blockType: string;
}) {
    const level = Math.min(Math.max(data.level ?? 1, 1), 4);
    const order = level as 1 | 2 | 3 | 4;
    const headerKind = resolveHeaderType(blockType, data);
    return (
        <Box className={`${classes.headerBlock} ${blockSurfaceClass(headerKind, role)}`}>
            <Title order={order} className={classes.headerTitle}>
                {data.text}
            </Title>
        </Box>
    );
}

function shouldRenderCardAsMarkdown(data: ReportCardData): boolean {
    const contentType = String(data.content_type ?? "").trim().toLowerCase();
    if (!contentType || contentType === "markdown" || contentType.includes("markdown")) {
        return true;
    }
    // content_type 오표기여도 본문에 MD 강조가 있으면 마크다운으로 렌더
    const content = data.content ?? "";
    return /(\*\*|__|`|^#{1,3}\s|^[-*]\s|^\d+\.\s)/m.test(content);
}

function KpiCardBlock({ items }: { items: ReportKpiItem[] }) {
    return (
        <Grid gutter="md">
            {items.map(item => (
                <Grid.Col key={item.label} span={{ base: 12, xs: 6, sm: 3 }}>
                    <Box className={classes.kpiItem}>
                        <Text size="xs" c="dimmed" tt="uppercase" fw={600}>{item.label}</Text>
                        <Text className={classes.kpiValue}>{item.value}</Text>
                        {item.delta && (
                            <Text size="xs" c="teal" mt={2}>{item.delta}</Text>
                        )}
                    </Box>
                </Grid.Col>
            ))}
        </Grid>
    );
}

function CardBlock({
    data,
    role,
    blockType,
}: {
    data: ReportCardData;
    role?: ReportBlockRole;
    blockType: string;
}) {
    const isKpi = blockType === "kpi_card" || data.card_type === "kpi" || role === "kpi_row";
    const dataStyle = extractDataStyle(data);
    const shellClass = blockShellClass(blockType, role, dataStyle);
    return (
        <Box className={`${classes.cardBlock} ${shellClass}`.trim()}>
            {data.title && (
                <Text component="div" fw={700} size="sm" mb="xs" className={classes.cardTitle}>
                    {data.title}
                </Text>
            )}
            {isKpi && Array.isArray(data.items) && data.items.length > 0 ? (
                <KpiCardBlock items={data.items} />
            ) : shouldRenderCardAsMarkdown(data) ? (
                <Box className={classes.markdownBody}>
                    <ReportMarkdown>{data.content ?? ""}</ReportMarkdown>
                </Box>
            ) : (
                <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>{data.content}</Text>
            )}
        </Box>
    );
}

function chartHasVisibleValues(option: EChartsOption): boolean {
    const series = Array.isArray(option.series) ? option.series : [];
    return series.some(item => {
        if (!item || typeof item !== "object") return false;
        const data = (item as { data?: unknown }).data;
        if (!Array.isArray(data)) return false;
        return data.some(point => {
            if (Array.isArray(point)) {
                return point.some(v => Number(v) !== 0);
            }
            if (point && typeof point === "object" && "value" in point) {
                const val = (point as { value?: unknown }).value;
                if (Array.isArray(val)) return val.some(v => Number(v) !== 0);
                return Number(val) !== 0;
            }
            return Number(point) !== 0;
        });
    });
}

function EchartBlock({
    data,
    role,
    blockType,
    templateId,
    patternId,
}: {
    data: ReportBlockData;
    role?: ReportBlockRole;
    blockType: string;
    templateId?: string;
    patternId?: string;
}) {
    const { option: rawOption, title, subtitle, insight } = normalizeEchartPresentation(data);
    if (!rawOption) {
        return (
            <Alert color="orange" variant="light" title="차트 데이터 오류">
                차트 옵션을 해석하지 못했습니다.
            </Alert>
        );
    }

    const option = applyReportChartTheme(rawOption, templateId, patternId);
    const baseHeight = blockType === "secondary_chart" || role === "secondary_chart" ? 300 : 400;
    const height = resolveReportChartHeight(option, baseHeight);
    const hasValues = chartHasVisibleValues(option);
    const dataStyle = extractDataStyle(data);
    const shellClass = blockShellClass(blockType, role, dataStyle);

    return (
        <Box className={`${classes.chartBlock} ${shellClass}`.trim()}>
            {(title || subtitle) && (
                <Box mb="sm">
                    {title && <Text className={classes.chartCaption}>{title}</Text>}
                    {subtitle && <Text className={classes.chartSubtitle}>{subtitle}</Text>}
                </Box>
            )}
            {!hasValues && (
                <Text size="xs" c="dimmed" mb="xs">
                    차트 축은 표시되지만 모든 수치가 0이라 막대/점이 보이지 않을 수 있습니다.
                </Text>
            )}
            <ECharts
                option={option}
                style={{ height, width: "100%" } as CSSProperties}
                notMerge
                lazyUpdate
                opts={{ renderer: "svg" }}
                onChartReady={chart => { chart.resize(); }}
            />
            {insight && (
                <Text size="sm" c="dimmed" mt="sm" className={classes.chartInlineInsight}>{insight}</Text>
            )}
        </Box>
    );
}

function formatCellValue(value: unknown, dtype?: ReportTableDtype): string {
    if (value === null || value === undefined) return "";
    if (dtype?.type === "number" || dtype?.type === "integer") {
        const n = Number(value);
        if (Number.isFinite(n)) {
            const decimals = dtype.decimals ?? (dtype.type === "integer" ? 0 : 2);
            return n.toLocaleString(undefined, {
                minimumFractionDigits: decimals,
                maximumFractionDigits: decimals,
            });
        }
    }
    return String(value);
}

function isNumericDtype(dtype?: ReportTableDtype): boolean {
    return dtype?.type === "number" || dtype?.type === "integer";
}

function resolveTableRows(data: ReportTableData): Record<string, unknown>[] {
    if (Array.isArray(data.data)) return data.data;
    if (Array.isArray(data.rows)) return data.rows;
    return [];
}

function layoutHasDocumentTitle(blocks: ReportLayoutBlock[]): boolean {
    for (const block of blocks) {
        if (block.type === "document_title") return true;
        if (block.blocks?.length) {
            if (layoutHasDocumentTitle(block.blocks)) return true;
        }
    }
    return false;
}

function shouldShowDocDescription(description?: string, title?: string): boolean {
    if (!description?.trim()) return false;
    const desc = description.trim();
    if (/초안/.test(desc)) return false;
    if (title && desc === title.trim()) return false;
    return desc.length <= 120;
}

function TableBlock({
    data,
    role,
    blockType,
}: {
    data: ReportTableData;
    role?: ReportBlockRole;
    blockType: string;
}) {
    const rows = resolveTableRows(data);
    const columns = resolveTableColumnSpecs(data, rows);
    const dataStyle = extractDataStyle(data);
    const shellClass = blockShellClass(blockType, role, dataStyle);

    if (columns.length === 0) {
        return (
            <Alert color="gray" variant="light">표 데이터가 비어 있습니다.</Alert>
        );
    }

    return (
        <Box className={`${classes.tableBlock} ${shellClass}`.trim()}>
            {data.title && (
                <Text className={classes.tableCaption}>{data.title}</Text>
            )}
            <Table.ScrollContainer minWidth={320}>
                <Table
                    striped
                    highlightOnHover
                    withTableBorder={false}
                    withColumnBorders={false}
                    className={classes.dataTable}
                >
                    <Table.Thead>
                        <Table.Tr>
                            {columns.map(col => (
                                <Table.Th key={col.key} className={classes.tableHeaderCell}>{col.label}</Table.Th>
                            ))}
                        </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                        {rows.map((row, i) => (
                            <Table.Tr key={i}>
                                {columns.map(col => {
                                    const numeric = isNumericDtype(col.dtype);
                                    return (
                                        <Table.Td
                                            key={col.key}
                                            className={numeric ? classes.tableNumericCell : undefined}
                                        >
                                            {formatCellValue(row[col.key], col.dtype)}
                                        </Table.Td>
                                    );
                                })}
                            </Table.Tr>
                        ))}
                    </Table.Tbody>
                </Table>
            </Table.ScrollContainer>
        </Box>
    );
}

function UnknownBlock({ type, blockKey, data }: { type: string; blockKey: string; data: unknown }) {
    return (
        <Alert color="yellow" variant="light" title={`미지원 블록: ${type}`}>
            <Text size="xs" c="dimmed" mb={6}>key: {blockKey}</Text>
            <pre className={classes.unknownPre}>{JSON.stringify(data, null, 2)}</pre>
        </Alert>
    );
}

function renderLeafBlock(
    block: ReportLayoutBlock,
    dataMap: Record<string, ReportBlockData>,
    templateId?: string,
    patternId?: string,
): ReactNode {
    const blockKey = block.key ?? block.type;
    const payload = block.key ? dataMap[block.key] : undefined;
    const type = block.type;

    if (block.key && payload === undefined) {
        return (
            <Alert key={blockKey} color="orange" variant="light">
                블록 데이터 없음: {block.key}
            </Alert>
        );
    }

    if (!payload) return null;

    const role = resolvePayloadRole(payload, type, block.role);

    if ((type === "document_title" || type === "section_title" || type === "header") && isHeaderData(payload)) {
        return <HeaderBlock key={blockKey} data={payload} role={role} blockType={type} />;
    }

    if (isCardBlockType(type) && isCardData(payload)) {
        return <CardBlock key={blockKey} data={payload} role={role} blockType={type} />;
    }

    if (isChartBlockType(type) && isEchartBlockData(payload)) {
        return (
            <EchartBlock
                key={blockKey}
                data={payload}
                role={role}
                blockType={type}
                templateId={templateId}
                patternId={patternId}
            />
        );
    }

    if (isTableBlockType(type) && isTableData(payload)) {
        return <TableBlock key={blockKey} data={payload} role={role} blockType={type} />;
    }

    // 형태 기반 fallback (레거시)
    if (isHeaderData(payload)) {
        return <HeaderBlock key={blockKey} data={payload} role={role} blockType={type} />;
    }
    if (isCardData(payload)) {
        return <CardBlock key={blockKey} data={payload} role={role} blockType={type} />;
    }
    if (isEchartBlockData(payload)) {
        return (
            <EchartBlock
                key={blockKey}
                data={payload}
                role={role}
                blockType={type}
                templateId={templateId}
                patternId={patternId}
            />
        );
    }
    if (isTableData(payload)) {
        return <TableBlock key={blockKey} data={payload} role={role} blockType={type} />;
    }

    return <UnknownBlock key={blockKey} type={type} blockKey={block.key ?? type} data={payload} />;
}

function renderLayoutNode(
    block: ReportLayoutBlock,
    dataMap: Record<string, ReportBlockData>,
    templateId?: string,
    patternId?: string,
    nodeKey = "root",
): ReactNode {
    if (isLayoutContainer(block)) {
        const children = block.blocks ?? [];
        const containerClass = block.type === "cols"
            ? classes.colsContainer
            : classes.rowsContainer;
        return (
            <Box key={nodeKey} className={containerClass} style={block.style as CSSProperties | undefined}>
                {children.map((child, index) =>
                    renderLayoutNode(child, dataMap, templateId, patternId, `${nodeKey}-${index}`),
                )}
            </Box>
        );
    }
    return renderLeafBlock(block, dataMap, templateId, patternId);
}

export type ReportDocumentRendererProps = {
    document: ReportDocumentBody;
    className?: string;
};

const TEMPLATE_THEME_CLASS: Record<string, string | undefined> = {
    "analytical-standard": classes.themeAnalyticalStandard,
    "financial-standard": classes.themeFinancialStandard,
};

/** layout 트리 순회 → 세분화 type + data.role 렌더 */
export function ReportDocumentRenderer({ document, className }: ReportDocumentRendererProps) {
    const themeKey = document.template_id ?? document.pattern_id ?? "default";
    const themeClass = TEMPLATE_THEME_CLASS[themeKey] ?? "";
    const blocks = document.layout?.blocks ?? [];
    const hasDocumentTitleBlock = layoutHasDocumentTitle(blocks);
    const showDocTitle = Boolean(document.title) && !hasDocumentTitleBlock;
    const showDocDescription = shouldShowDocDescription(document.description, document.title);

    return (
        <Box className={`${classes.root} ${themeClass ?? ""} ${className ?? ""}`}>
            <Box className={classes.pageCanvas}>
            {(showDocTitle || showDocDescription) && (
                <Box className={classes.docMeta} mb="md">
                    {showDocTitle && document.title && (
                        <Title order={2} className={classes.docTitle}>{document.title}</Title>
                    )}
                    {showDocDescription && document.description && (
                        <Text size="sm" c="dimmed" mt={4}>{document.description}</Text>
                    )}
                </Box>
            )}
            {document.quality && !document.quality.passed && (
                <Alert color="yellow" variant="light" mb="md" title={`구성 품질 점수: ${document.quality.score}`}>
                    {document.quality.issues.slice(0, 3).map(issue => (
                        <Text key={issue.code} size="xs">• {issue.message}</Text>
                    ))}
                </Alert>
            )}
            <Box className={classes.blocks}>
                {blocks.map((block, index) =>
                    renderLayoutNode(
                        block,
                        document.data ?? {},
                        document.template_id,
                        document.pattern_id,
                        `block-${index}`,
                    ),
                )}
            </Box>
            </Box>
        </Box>
    );
}

export type ReportResultPanelProps = {
    result: ReportGenerateResult | null;
    isLoading?: boolean;
    error?: string | null;
    emptyMessage?: string;
    scrollable?: boolean;
};

export function ReportResultPanel({
    result,
    isLoading,
    error,
    emptyMessage = "보고서를 생성하면 이 영역에 결과가 표시됩니다.",
    scrollable = true,
}: ReportResultPanelProps) {
    if (isLoading) {
        return (
            <Box className={classes.panelEmpty}>
                <Text size="sm" c="dimmed">보고서를 생성하고 있습니다...</Text>
            </Box>
        );
    }

    if (error) {
        return (
            <Alert color="red" variant="light" title="보고서 생성 실패">
                {error}
            </Alert>
        );
    }

    if (!result?.report) {
        return (
            <Box className={classes.panelEmpty}>
                <Text size="sm" c="dimmed">{emptyMessage}</Text>
            </Box>
        );
    }

    if (!scrollable) {
        return <ReportDocumentRenderer document={result.report} />;
    }

    return (
        <ScrollArea className={classes.panelScroll} type="auto">
            <ReportDocumentRenderer document={result.report} />
        </ScrollArea>
    );
}
