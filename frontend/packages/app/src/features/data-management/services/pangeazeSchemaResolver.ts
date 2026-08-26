import type { SageData } from "@/features/data";
import { resolvePangeaSchemaFields } from "@/features/data/pangeaSchemaUtils";
import type { PangeazeSchemaObject, Schema } from "@/features/data-analysis";

const SCHEMA_META_KEYS = new Set([
    "type", "title", "required", "description",
    "additionalProperties", "$schema", "properties",
]);

function isFieldSchema(value: unknown): value is Schema {
    return typeof value === "object"
        && value !== null
        && ("type" in value || "title" in value || "properties" in value);
}

/** JSON Schema object → properties 맵 (테이블 렌더용) */
export function resolveSchemaPropertyMap(
    schema: PangeazeSchemaObject | null | undefined,
): Record<string, Schema> {
    if (!schema || typeof schema !== "object") return {};

    if (schema.properties && typeof schema.properties === "object") {
        return schema.properties;
    }

    const map: Record<string, Schema> = {};
    for (const [key, value] of Object.entries(schema)) {
        if (SCHEMA_META_KEYS.has(key)) continue;
        if (isFieldSchema(value)) {
            map[key] = value;
        }
    }
    return map;
}

function wrapAsSchemaObject(raw: unknown): PangeazeSchemaObject | null {
    if (!raw || typeof raw !== "object") return null;

    const obj = raw as Record<string, unknown>;

    if (obj.properties && typeof obj.properties === "object") {
        return obj as PangeazeSchemaObject;
    }

    const properties = resolveSchemaPropertyMap(obj as PangeazeSchemaObject);
    if (Object.keys(properties).length === 0) return null;

    return {
        type: typeof obj.type === "string" ? obj.type : "object",
        title: typeof obj.title === "string" ? obj.title : undefined,
        properties,
    };
}

/** Pangeaze SSE 청크에서 schema 추출 (경로·형식 차이 흡수) */
export function extractPangeazeSchema(
    chunk: Record<string, unknown>,
): PangeazeSchemaObject | null {
    const candidates: unknown[] = [
        chunk.schema,
        chunk.confirmed_schema,
        (chunk.result as Record<string, unknown> | undefined)?.schema,
        (chunk.datasets as unknown),
    ];

    for (const candidate of candidates) {
        const wrapped = wrapAsSchemaObject(candidate);
        if (wrapped) return wrapped;
    }

    return null;
}

/** List Data pangea[] → 우측 패널 schemaResult (기등록 모델 로드용) */
export function resolveSchemaFromSageData(data: SageData): PangeazeSchemaObject | null {
    const entries = data.pangea;
    if (Array.isArray(entries)) {
        for (const entry of entries) {
            if (entry && typeof entry === "object") {
                const schema = extractPangeazeSchema(entry as Record<string, unknown>);
                if (schema) return schema;
            }
        }
    }

    const fields = resolvePangeaSchemaFields(data);
    if (fields.length === 0) return null;

    const properties: Record<string, Schema> = {};
    for (const { name, type } of fields) {
        properties[name] = {
            type: type === "—" ? "string" : type,
        };
    }

    return {
        type: "object",
        title: data.name,
        properties,
    };
}
