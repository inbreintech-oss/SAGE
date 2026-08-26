import type { SageData } from "./api";

type PangeaMetadataTarget = {
    model?: string;
    fields?: string[];
};

type PangeaMetadata = {
    targets?: PangeaMetadataTarget[];
};

type PangeaEntry = {
    metadata?: PangeaMetadata;
};

export type SchemaFieldRow = {
    name: string;
    type: string;
};

/** List Data pangea[] 에서 표준 스키마 필드 목록 추출 */
export function resolvePangeaSchemaFields(data: SageData): SchemaFieldRow[] {
    const entries = data.pangea as PangeaEntry[] | undefined;
    if (!entries?.length) return [];

    const targets = entries[0]?.metadata?.targets;
    const fields = targets?.[0]?.fields;
    if (!Array.isArray(fields)) return [];

    return fields.map(name => ({ name, type: "—" }));
}

export function resolvePangeaFieldCount(data: SageData): number {
    return resolvePangeaSchemaFields(data).length;
}
