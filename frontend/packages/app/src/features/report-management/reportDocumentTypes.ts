/**
 * Report Document — 3안: type 세분화 + data.role
 */

export type ReportBlockRole =
    | "report_title"
    | "section_header"
    | "executive_summary"
    | "key_findings"
    | "metrics_table"
    | "primary_chart"
    | "secondary_chart"
    | "chart_insight"
    | "table_insight"
    | "conclusions"
    | "methodology"
    | "appendix_table"
    | "kpi_row"
    | string;

export type ReportDataStyle = {
    variant?: "default" | "emphasis" | "muted" | "highlight" | "callout";
    accent?: string;
    density?: "compact" | "normal" | "spacious";
    border?: boolean;
};

/** 세분화 + 레거시 + 컨테이너 */
export type ReportBlockType =
    | "document_title"
    | "section_title"
    | "summary_card"
    | "insight_card"
    | "kpi_card"
    | "text_card"
    | "closing_card"
    | "metrics_table"
    | "appendix_table"
    | "primary_chart"
    | "secondary_chart"
    | "header"
    | "card"
    | "echart"
    | "chart"
    | "table"
    | "rows"
    | "cols"
    | string;

export type ReportPayloadMeta = {
    /** lint · 보조 스타일 (closed enum) */
    role?: ReportBlockRole;
    description?: string;
    style?: ReportDataStyle;
};

export type ReportLayoutBlock = {
    type: ReportBlockType;
    key?: string;
    task_id?: string;
    /** @deprecated data[key].role 사용 */
    role?: ReportBlockRole;
    style?: Record<string, unknown>;
    blocks?: ReportLayoutBlock[];
};

export type ReportLayout = {
    type?: string;
    blocks: ReportLayoutBlock[];
    style?: Record<string, unknown>;
};

export type ReportHeaderData = ReportPayloadMeta & {
    text: string;
    level?: number;
};

export type ReportKpiItem = {
    label: string;
    value: string;
    delta?: string;
};

export type ReportCardData = ReportPayloadMeta & {
    title?: string;
    content?: string;
    content_type?: "markdown" | string;
    card_type?: "kpi" | string;
    items?: ReportKpiItem[];
};

export type ReportTableDtype = {
    type?: string;
    decimals?: number;
};

export type ReportTableData = ReportPayloadMeta & {
    title?: string;
    header?: string[];
    dtypes?: Record<string, ReportTableDtype>;
    data?: Record<string, unknown>[];
    columns?: ReportTableColumn[] | string[];
    rows?: Record<string, unknown>[];
};

export type ReportTableColumn = {
    key?: string;
    name?: string;
    title?: string;
    label?: string;
};

export type ReportEchartData = ReportPayloadMeta & Record<string, unknown>;

export type ReportBlockData =
    | ReportHeaderData
    | ReportCardData
    | ReportEchartData
    | ReportTableData
    | Record<string, unknown>;

export type ReportQualityIssue = {
    level: string;
    code: string;
    message: string;
    key?: string;
    role?: string;
};

export type ReportQualityMeta = {
    score: number;
    passed: boolean;
    issues: ReportQualityIssue[];
};

export type ReportDocumentBody = {
    title?: string;
    description?: string;
    template_id?: string;
    pattern_id?: string;
    version?: number;
    plan_id?: string;
    did?: string;
    rid?: string;
    layout: ReportLayout;
    data: Record<string, ReportBlockData>;
    quality?: ReportQualityMeta;
};

export type ReportPlanTask = {
    task_id: string;
    type?: string;
    title?: string;
    description?: string;
    instruction?: string;
    context?: string[];
    tools?: string[];
};

export type ReportPlan = {
    plan_id?: string;
    title?: string;
    description?: string;
    data_id?: string;
    tools?: string[];
    tasks?: ReportPlanTask[];
};

export type ReportGenerateResult = {
    plan?: ReportPlan;
    rid?: string;
    report_dir?: string;
    report: ReportDocumentBody;
};

export function isReportGenerateResult(value: unknown): value is ReportGenerateResult {
    if (!value || typeof value !== "object") return false;
    const obj = value as Record<string, unknown>;
    const report = obj.report;
    if (!report || typeof report !== "object") return false;
    const layout = (report as Record<string, unknown>).layout;
    if (!layout || typeof layout !== "object") return false;
    return Array.isArray((layout as Record<string, unknown>).blocks);
}

export function unwrapReportGenerateResult(raw: unknown): ReportGenerateResult {
    if (isReportGenerateResult(raw)) return raw;

    if (raw && typeof raw !== "object") {
        throw new Error("보고서 생성 응답 형식이 올바르지 않습니다.");
    }

    const obj = raw as Record<string, unknown>;

    if (isReportGenerateResult(obj.result)) return obj.result;

    if (obj.result && typeof obj.result === "object") {
        const nested = obj.result as Record<string, unknown>;
        if (isReportGenerateResult(nested)) return nested;
        if (nested.report && typeof nested.report === "object") {
            return nested as unknown as ReportGenerateResult;
        }
        if (isReportGenerateResult(nested.result)) {
            return nested.result;
        }
    }

    if (obj.report && typeof obj.report === "object") {
        const layout = (obj.report as Record<string, unknown>).layout;
        if (layout && typeof layout === "object" && Array.isArray((layout as { blocks?: unknown }).blocks)) {
            return obj as unknown as ReportGenerateResult;
        }
    }

    throw new Error("보고서 생성 응답 형식이 올바르지 않습니다.");
}

export type ReportTableColumnSpec = {
    key: string;
    label: string;
    dtype?: ReportTableDtype;
};

/** header 표시 라벨과 data 행 dict 키가 다를 때 table_spec 규칙으로 정렬 */
export function resolveTableColumnSpecs(
    data: ReportTableData,
    rows: Record<string, unknown>[],
): ReportTableColumnSpec[] {
    const rowKeys = rows.length > 0 ? Object.keys(rows[0]) : [];
    const dtypeKeys = data.dtypes ? Object.keys(data.dtypes) : [];

    if (Array.isArray(data.columns) && data.columns.length > 0) {
        return data.columns.map(col => {
            if (typeof col === "string") {
                return {
                    key: col,
                    label: col,
                    dtype: data.dtypes?.[col],
                };
            }
            const key = col.key ?? col.name ?? col.title ?? col.label ?? "";
            const label = col.label ?? col.title ?? col.name ?? key;
            return { key, label, dtype: data.dtypes?.[key] };
        }).filter(spec => spec.key);
    }

    const headers = Array.isArray(data.header) ? data.header : [];
    if (headers.length > 0) {
        const keysMatch = rows.length > 0
            && headers.every(h => typeof h === "string" && h in rows[0]);
        if (!keysMatch) {
            const keys = dtypeKeys.length === headers.length
                ? dtypeKeys
                : rowKeys.length === headers.length
                    ? rowKeys
                    : rowKeys;
            return headers.map((label, index) => {
                const key = keys[index] ?? label;
                return {
                    key,
                    label,
                    dtype: data.dtypes?.[key],
                };
            });
        }
        return headers.map(label => ({
            key: label,
            label,
            dtype: data.dtypes?.[label],
        }));
    }

    if (rowKeys.length > 0) {
        return rowKeys.map(key => ({
            key,
            label: key,
            dtype: data.dtypes?.[key],
        }));
    }

    return [];
}

export function isTableData(data: ReportBlockData): data is ReportTableData {
    if (!data || typeof data !== "object") return false;
    const d = data as ReportTableData;
    return Array.isArray(d.header)
        || Array.isArray(d.rows)
        || (Array.isArray(d.data) && d.data.length > 0 && typeof d.data[0] === "object")
        || Array.isArray(d.columns);
}

export function isCardData(data: ReportBlockData): data is ReportCardData {
    if (!data || typeof data !== "object") return false;
    const d = data as ReportCardData;
    if (d.card_type === "kpi" && Array.isArray(d.items)) return true;
    if (Array.isArray(d.items) && d.items.length > 0) return true;
    return typeof d.content === "string";
}

export function isHeaderData(data: ReportBlockData): data is ReportHeaderData {
    return typeof data === "object" && data !== null && "text" in data && typeof (data as ReportHeaderData).text === "string";
}
