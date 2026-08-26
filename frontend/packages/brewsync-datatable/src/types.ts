import {
    Column,
    ColumnDef,
    RowData, Table,
    TableMeta,
    TableOptions, TableState
} from "@tanstack/react-table";
import {CSSProperties} from "react";
import {DensityInstance, DensityOptions, DensityTableState} from "@/features/density";
import {
    EditingCellConfig,
    CodePickerEditingConfig,
    RowEditingOptions,
    RowEditingTableState
} from "@/features/rowEditing";

export type { CodePickerEditingConfig };
import {RowClickOptions} from "@/features/rowClick";

export type TextAlign = "left" | "center" | "right";

export type Stripe = "odd" | "even" | false;

/*
    https://chatgpt.com/c/690c4f1f-0134-8323-aeaf-e814aa098123
    https://tanstack.com/table/latest/docs/framework/react/guide/table-state#fully-controlled-state

    onStateChange -> Render? 어떻게?
        -> State를 가져다 쓰는거니까 React가 Render.

    Prefix: BrewSync
        - TableInstance (onStateChange를 사용한 FullControlled State, Wrapper) ** 신규
            > _table: Table - ReactTable 기능 인스턴스
            > set[State]() - Custom 작업
        - ColumnDef (Meta를 포함한, BrewSyncColumnDef)
        - TableDef? DefOptions? (TableDef를 포함한, BrewSyncTableOptions)
        - State (Custom 기능을 포함한) ** 작업 필요

 */

/**
 * BrewSync Table Instance 타입입니다.
 * React Table을 Wrapping 하기 위해 사용합니다.
 */
export type BrewSyncTableInstance<TData extends RowData> = {
} & Table<TData>

export type BrewSyncTableOptions<TData extends RowData> = {
    columns: BrewSyncColumnDef<TData>[],
    state: Partial<TableState>,
    initialState?: Partial<TableState>,
    onRowSelectionChange?: (selectedRowIds: string[]) => void;
} & TableMeta<TData> & Omit<TableOptions<TData>,"columns" | "state" | "initialState">

/**
 * Column Definition Type
 */
export type BrewSyncColumn<TData extends RowData, TValue> = {
} & Column<TData, TValue>

/**
 * BrewSync Column Definition
 *
 * 주의: meta 속성에는 상위 레벨 옵션들(headerAlign, contentAlign, cellFormat 등)을 직접 넣지 마세요.
 * 이 옵션들은 상위 레벨에서 정의하면 자동으로 meta로 매핑됩니다.
 *
 * @example
 * // ✅ 올바른 사용법
 * {
 *   accessorKey: "price",
 *   header: "가격",
 *   headerAlign: "center",
 *   contentAlign: "right",
 *   cellFormat: {
 *     type: "numeric",
 *     currencySymbol: "₩"
 *   }
 * }
 *
 * @example
 * // ❌ 잘못된 사용법 (타입 에러 발생)
 * {
 *   accessorKey: "price",
 *   header: "가격",
 *   meta: {
 *     headerAlign: "center",  // 타입 에러!
 *     cellFormat: { ... }      // 타입 에러!
 *   }
 * }
 */
export type BrewSyncColumnDef<TData extends RowData> = {
    /** 헤더 정렬 */
    headerAlign?: TextAlign;
    /** 내용 정렬 */
    contentAlign?: TextAlign;
    /** 셀 값 포맷팅 옵션 */
    cellFormat?: CellFormatOptions;
    /** 편집 가능 여부 */
    enableEditing?: boolean;
    /** 편집 셀 설정 */
    editingConfig?: EditingCellConfig;
    /** 컬럼 표시 여부 */
    visibility?: boolean;
} & Omit<ColumnDef<TData>, 'meta'> & {
    /**
     * meta 속성 (상위 레벨 옵션 제외)
     *
     * 주의: headerAlign, contentAlign, cellFormat, enableEditing, editingConfig는
     * 상위 레벨에서 정의해야 합니다. meta에 직접 넣으면 타입 에러가 발생합니다.
     */
    meta?: Omit<ColumnDef<TData>['meta'],
        'headerAlign' | 'contentAlign' | 'cellFormat' | 'enableEditing' | 'editingConfig'
    >;
}

export type Prettify<T> = { [K in keyof T]: T[K] } & unknown;

export type Xor<A, B> =
    | Prettify<{ [k in keyof A]?: never } & B>
    | Prettify<{ [k in keyof B]?: never } & A>;

export interface BrewSyncTableMeta {
    tableWidth?: CSSProperties["width"];
    tableHeight?: CSSProperties["height"];
    withTableBorder?: boolean;
    withColumnBorder?: boolean;
    withRowBorder?: boolean;
    withStripe?: Stripe;
    withHighlightOnHover?: boolean;
    enablePagination?: boolean;
    enableDelete?: boolean;
    stickyHeader?: boolean;
    defaultPageSizes?: string[];
}

export type ColumnType = "text" | "number" | "select" | "date" | "boolean" | "codePicker";

export type NumericFormatOptions = {
    type: "numeric";
    /** 1000단위 구분자 사용 여부 (default: true) */
    useGrouping?: boolean;
    /** 통화 기호 (예: "$", "₩", "€") */
    currencySymbol?: string;
    /** 소수점 자릿수 (default: 0) */
    maximumFractionDigits?: number;
    /** 최소 소수점 자릿수 (default: 0) */
    minimumFractionDigits?: number;
};

export type DateFormatOptions = {
    type: "date";
    /** dayjs 포맷 스트링 (default: "YYYY-MM-DD") */
    format?: string;
};

export type BooleanFormatOptions = {
    type: "boolean";
    /** true일 때 표시할 텍스트 (default: "Yes") */
    trueLabel?: string;
    /** false일 때 표시할 텍스트 (default: "No") */
    falseLabel?: string;
};

export type SelectFormatOptions = {
    type: "select";
    options: Array<{ value: string; label: string }>;
};

export type CodePickerFormatOptions = {
    type: "codePicker";
    codeGroupId: string;
    companyAppId: number;
    mode: "code" | "codeHelp";
    multiple?: boolean;
    codeColumnId?: string;
    valueColumnId?: string;
    query?: {
        data?: { items?: Array<Record<string, unknown>> };
        isLoading?: boolean;
        isFetching?: boolean;
    };
    data?: Array<Record<string, unknown>>;
    resolveLabel?: (item: Record<string, unknown>) => string;
};

export type CellFormatOptions =
    | NumericFormatOptions
    | DateFormatOptions
    | BooleanFormatOptions
    | SelectFormatOptions
    | CodePickerFormatOptions;

declare module "@tanstack/react-table" {
    interface ColumnMeta<TData extends RowData, TValue> {
        headerAlign?: TextAlign;
        contentAlign?: TextAlign;
        enableEditing?: boolean;
        editingConfig?: EditingCellConfig;
        /** 셀 값 포맷팅 옵션 */
        cellFormat?: CellFormatOptions;
    }

    interface TableMeta<TData extends RowData> extends BrewSyncTableMeta {}

    interface TableState extends
        DensityTableState,
        RowEditingTableState
    {}

    interface TableOptionsResolved<TData extends RowData> extends
        DensityOptions,
        RowEditingOptions<TData>,
        RowClickOptions<TData>
    {}

    interface Table<TData extends RowData> extends
        DensityInstance
    {}
}
