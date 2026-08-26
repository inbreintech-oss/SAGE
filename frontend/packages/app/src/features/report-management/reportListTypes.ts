/** Report API v1.1 — 목록·등록·실행 */

export type ReportApiStatus = "completed" | "published" | "initializing" | string;

export type ReportListItem = {
    rid: string;
    did?: string;
    plan_id?: string;
    title?: string;
    description: string;
    status: ReportApiStatus;
    query?: string;
    tools?: string[];
    version?: number;
    session_id?: string;
    created_at?: string;
    updated_at?: string;
};

export type ReportListQueryPayload = {
    status?: ReportApiStatus[];
};

export type ReportListQueryResponse = {
    success: boolean;
    error: string | null;
    result: ReportListItem[];
};

export type PublishReportPayload = {
    rid: string;
};

export type PublishReportResponse = {
    success: boolean;
    error: string | null;
    result: ReportListItem;
};

export type ExecReportPayload = {
    rid: string;
};
