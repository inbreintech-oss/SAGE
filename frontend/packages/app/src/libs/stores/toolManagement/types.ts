import type { ToolApiStatus } from "@/features/tool/api";

export type ToolLifecycleStage = "draft" | "generated" | "assetized";

export type ToolAssetStatus = "generated" | "assetized";

export type ToolEditorMode = "idle" | "new" | "existing" | "clone";

export type ToolListItem = {
    tool_id: string;
    title: string;
    description: string;
    category: string;
    keyword: string;
    query: string;
    code: string;
    default_parameters: Record<string, string>;
    status: ToolAssetStatus;
    apiStatus: ToolApiStatus;
    /** /secret/list secret_id */
    provider: string;
    /** 연계기관 인증 토큰 도구 tool_id (optional) */
    tokenToolId?: string;
    recommendationQuery?: string;
    created_at: string;
    updated_at: string;
};

export type ToolFormDraft = {
    sourceToolId: string | null;
    title: string;
    description: string;
    category: string;
    keyword: string;
    query: string;
    code: string;
    /** /secret/list secret_id */
    provider: string;
    /** 연계기관 인증 토큰 도구 tool_id (optional) */
    tokenToolId: string;
    execParamName: string;
    execParamValue: string;
    execQuery: string;
};

export type UiButtonState = "unselected" | "new" | "generated" | "assetized";

export type OriginSelectedToolCache = ToolFormDraft;

export type ToolSearchQuery = {
    raw: string;
    orTokens: string[];
};

export type VisualResultType = "formula" | "dataset" | "empty" | "error";

export type VisualResult = {
    type: VisualResultType;
    latex?: string;
    tableHeaders?: string[];
    tableRows?: Record<string, unknown>[];
    message?: string;
};

export type SaveAttemptResult =
    | { allowed: true; pipeline: "CREATE" | "CLONE" }
    | {
          allowed: false;
          reason: "VALIDATION_FAILED" | "SCHEMA_ALREADY_EXISTS" | "ALREADY_SAVED" | "DUPLICATE_TITLE";
          message: string;
          invalidFields?: (keyof ToolFormDraft)[];
      };

export type AssetizeAttemptResult =
    | { allowed: true }
    | {
          allowed: false;
          reason: "SCHEMA_ALREADY_EXISTS" | "DUPLICATE_TITLE" | "VALIDATION_FAILED";
          message: string;
          invalidFields?: (keyof ToolFormDraft)[];
      };

export type ExecAttemptResult =
    | { allowed: true }
    | { allowed: false; reason: "NO_SAVE_POINT" | "EMPTY_PARAM"; message: string };

export type RequiredFormField =
    | "title"
    | "description"
    | "category"
    | "keyword"
    | "query";
