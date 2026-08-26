import {FetchAPI, fetchSSEStream} from "@/features/Utils.ts";

const API_BASE_URL = "/api";

export type Column = {
    fileName: string;
    sheetName: string;
    name: string;
    dtype: string;
};

export type Metadata = {
    fileName: string;
    name: string;
    columns: Column[];
};

export type UploadedFile = {
    path: string;
    filename: string;
    file_type: string;
    metadata: Metadata[];
};

export type { DataSource } from "@/features/data";

export type UploadDataPayload = {
    file: File | null;
}

export async function uploadDataFile(payload: UploadDataPayload): Promise<UploadedFile> {
    const formData = new FormData();
    if (payload.file) {
        formData.append("file", payload.file);
    }

    const response = await FetchAPI<UploadedFile>(`${API_BASE_URL}/data/upload`, "POST", {
        body: formData,
        // headers를 비워두어야 브라우저가 boundary를 자동으로 설정합니다.
    });

    // 관계 데이터 설정
    response.metadata.forEach(item => {
        const sheetName = item.name;
        item.fileName = response.filename;

        item.columns.forEach(col => {
            col.sheetName = sheetName;
            col.fileName = response.filename;
        })
    });

    return response;
}

export type RegisterDataPayload = {
    description: string;
    name: string;
    options: {
        pseudonymization: boolean;
    },
    sources: DataSource[]
};

export type RegisterDataResponse = {
    did: string;
};

export async function registerData(
    payload: RegisterDataPayload
): Promise<RegisterDataResponse> {
    return FetchAPI(`${API_BASE_URL}/data/register`, "POST", {
        body: JSON.stringify(payload),
    });
}

export type AnalyzeSchemaPayload = {
    did: string;
    query: string;
};

export type AnalyzeSchemaResponse = {
    eventType: string;
    msg: string;
    analysis_result?: AnalyzeSchemaResult;
}

export type AnalyzeSchemaResult = {
    schema: Record<string, Schema>;
    mapping: Record<string, string>;
    logic: string;
    raw_code: string;
}

export type Schema = {
    title: string;
    description: string;
    type?: string;
    [key: string]: unknown;
}

export async function analyzeSchema(
    payload: AnalyzeSchemaPayload,
    signal?: AbortSignal
) {
    return fetchSSEStream(
        `${API_BASE_URL}/data/pangea/analyze`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
            body: JSON.stringify(payload),
        },
        signal
    )
}

export type UnifySchemaPayload = {
    did: string;
    confirmed_schema?: Record<string, Schema>;
};

export type UnifySchemaResponse = {
    msg: string;
    did?: string;
    version?: string;
}

export async function unifySchema(
    payload: UnifySchemaPayload,
    signal?: AbortSignal
)  {
    return fetchSSEStream(
        `${API_BASE_URL}/data/pangea/unify`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
        },
        signal
    )
}

export type PangeazePayload = {
    name: string;
    description: string;
    query: string;
    sources: DataSource[];
    /** Data API v1.3 */
    category?: string;
};

export type PangeazeSchemaObject = {
    properties: Record<string, Schema>;
    required?: string[];
    title?: string;
    type?: string;
};

export type PangeazeResponse = {
    eventType: string;
    msg: string;
    did?: string;
    version?: string;
    schema?: PangeazeSchemaObject;
    /** Pangeaze completed 시 모델별 추천 질의문 */
    suggested_queries?: string[];
}

export async function pangeaze(
    payload: PangeazePayload,
    signal?: AbortSignal
) {
    return fetchSSEStream(
        `${API_BASE_URL}/data/pangeaze`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
            body: JSON.stringify(payload),
        },
        signal
    );
}

export type UpdatePangeazePayload = {
    did: string;
    confirmed_schema?: Record<string, Schema>;
};

export type UpdatePangeazeResponse = {
    eventType: string;
    msg: string;
    did?: string;
    version?: string;
}

export async function updatePangeaze(
    payload: UpdatePangeazePayload,
    signal?: AbortSignal
)  {
    return fetchSSEStream(
        `${API_BASE_URL}/data/pangeaze/update`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
            body: JSON.stringify(payload),
        },
        signal
    )
}