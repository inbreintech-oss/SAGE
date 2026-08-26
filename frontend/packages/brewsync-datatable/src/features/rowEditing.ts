import {
    Cell,
    makeStateUpdater,
    OnChangeFn,
    Row,
    RowData,
    Table,
    TableFeature,
    Updater
} from "@tanstack/react-table";

/**
 * 편집 가능한 컬럼 타입 옵션
 */
export type TextEditingConfig = {
    type: "text";
    required?: boolean;
    maxLength?: number;
};

export type SelectEditingConfig = {
    type: "select";
    options: Array<{ value: string; label: string }>;
    required?: boolean;
};

export type DateEditingConfig = {
    type: "date";
    format?: string;
    withSeconds?: boolean;
    required?: boolean;
};

export type BooleanEditingConfig = {
    type: "boolean";
    required?: boolean;
};

export type CodePickerEditingConfig = {
    type: "codePicker";
    codeGroupId: string;
    companyAppId: number;
    mode: "code" | "codeHelp";
    multiple?: boolean;
    codeColumnId?: string;
    valueColumnId?: string;
    required?: boolean;

    // ReactQuery 결과를 직접 전달
    query?: {
        data?: { items?: Array<Record<string, unknown>> };
        isLoading?: boolean;
        isFetching?: boolean;
    };

    // 고정 목록 데이터 (query 대신 사용 가능)
    data?: Array<Record<string, unknown>>;

    resolveLabel?: (item: Record<string, unknown>) => string;
};

export type EditingCellConfig =
    | TextEditingConfig
    | SelectEditingConfig
    | DateEditingConfig
    | BooleanEditingConfig
    | CodePickerEditingConfig;

/**
 * 편집 가능한 컬럼 타입 (하위 호환성을 위해 유지)
 */
export type EditingCellType = "text" | "select" | "date" | "boolean" | "codePicker";

/**
 * Row Editing State
 */
export type RowEditingState = Record<string, Record<string, any> & { __errors?: Record<string, string> }>;

/**
 * Row Editing Table State
 */
export interface RowEditingTableState {
    rowEditing: RowEditingState;
}

/**
 * Row Editing Options
 */
export interface RowEditingOptions<TData extends RowData> {
    enableRowEditing?: boolean | ((row: Row<TData>) => boolean);
    onRowEditingChanged?: OnChangeFn<RowEditingState>;
    onRowEditingSave?: (rowId: string, data: Record<string, any>) => void | Promise<void>;
    onRowEditingDelete?: (rowId: string, data: Record<string, any>) => void | Promise<void>;
}

/**
 * Row Editing Row API
 */
export interface RowEditingRow<TData extends RowData> {
    getIsEditing: () => boolean;
    getCanEdit: () => boolean;
    getEditingData: () => Record<string, any> | undefined;

    startEditing: () => void;
    saveEditing: (data?: Record<string, any>) => Promise<void>;
    cancelEditing: () => void;
    deleteRow: () => Promise<void>;
    updateEditingCell: (columnId: string, value: any) => void;
}

/**
 * Row Editing Cell API
 */
export interface RowEditingCell<TData extends RowData, TValue> {
    getEditingValue: () => TValue;
    getEditingError: () => string | undefined;
    updateEditingValue: (value: any) => void;
}

/**
 * Row Editing Instance API
 */
export interface RowEditingInstance<TData extends RowData> {
    setRowEditing: (updater: Updater<RowEditingState>) => void;
    resetRowEditing: () => void;
    getEditingRows: () => Row<TData>[];
}

/**
 * Row Editing Feature
 */
export const RowEditing: TableFeature = {
    getInitialState: (state): RowEditingTableState => {
        return {
            rowEditing: {},
            ...state,
        }
    },

    getDefaultOptions: <TData extends RowData>(
        table: Table<TData>
    ): RowEditingOptions<TData> => {
        return {
            enableRowEditing: true,
            onRowEditingChanged: makeStateUpdater("rowEditing", table),
        }
    },

    createTable: <TData extends RowData>(
        table: Table<TData>
    ): void => {
        table.setRowEditing = (updater) => {
            table.options.onRowEditingChanged?.(updater);
        };

        table.resetRowEditing = () => {
            table.setRowEditing({});
        };

        table.getEditingRows = () => {
            const { rowEditing } = table.getState();
            return Object.keys(rowEditing)
                .map(rowId => table.getRow(rowId))
                .filter(Boolean);
        };
    },

    createRow: <TData extends RowData>(
        row: Row<TData>,
        table: Table<TData>
    ): void => {
        row.getIsEditing = () => {
            const { rowEditing } = table.getState();
            return !!rowEditing[row.id];
        };

        row.getCanEdit = () => {
            const { enableRowEditing } = table.options;
            if (enableRowEditing === undefined) return false;
            if (typeof enableRowEditing === "function") return enableRowEditing(row);
            return enableRowEditing;
        };

        row.getEditingData = () => {
            const { rowEditing } = table.getState();
            return rowEditing[row.id];
        };

        row.startEditing = () => {
            if (!row.getCanEdit()) return;

            const initialData = row.getAllCells().reduce<Record<string, any>>((acc, cell) => {
                acc[cell.column.id] = cell.getValue();
                return acc;
            }, {});

            table.setRowEditing(old => ({
                ...old,
                [row.id]: initialData
            }));
        };

        row.saveEditing = async (data?: Record<string, any>) => {
            const editingData = data ?? row.getEditingData();
            if (!editingData) return;

            // 유효성 검사
            const errors: Record<string, string> = {};
            row.getAllCells().forEach(cell => {
                const config = cell.column.columnDef.meta?.editingConfig;
                if (config?.required) {
                    const val = editingData[cell.column.id];
                    if (val === undefined || val === null || val === "") {
                        errors[cell.column.id] = "필수 입력 항목입니다.";
                    }
                }
            });

            if (Object.keys(errors).length > 0) {
                // 에러가 있으면 상태 업데이트
                table.setRowEditing(old => ({
                    ...old,
                    [row.id]: {
                        ...editingData,
                        __errors: errors
                    }
                }));
                return;
            }

            const { onRowEditingSave } = table.options;
            if (onRowEditingSave) {
                // __errors 필드 제외하고 전달
                const { __errors, ...pureData } = editingData;
                await onRowEditingSave(row.id, pureData);
            }

            table.setRowEditing(old => {
                const next = { ...old };
                delete next[row.id];
                return next;
            });
        };

        row.cancelEditing = () => {
            table.setRowEditing(old => {
                const next = { ...old };
                delete next[row.id];
                return next;
            });
        };

        row.deleteRow = async () => {
            const { onRowEditingDelete } = table.options;
            if (onRowEditingDelete) {
                await onRowEditingDelete(row.id, row.original as Record<string, any>);
            }
        };

        row.updateEditingCell = (columnId: string, value: any) => {
            if (!row.getIsEditing()) return;

            table.setRowEditing(old => ({
                ...old,
                [row.id]: {
                    ...old[row.id],
                    [columnId]: value
                }
            }));
        };
    },

    createCell: <TData extends RowData, TValue>(
        cell: Cell<TData, TValue>,
        column: any,
        row: Row<TData>,
        table: Table<TData>
    ): void => {
        cell.getEditingValue = () => {
            const editingData = row.getEditingData();
            if (!editingData) return cell.getValue();
            return editingData[column.id] ?? cell.getValue();
        };

        cell.getEditingError = () => {
            const editingData = row.getEditingData();
            if (!editingData) return undefined;
            return editingData.__errors?.[column.id];
        };

        cell.updateEditingValue = (value: any) => {
            row.updateEditingCell(column.id, value);
        };
    }
};

declare module "@tanstack/react-table" {
    interface TableState extends RowEditingTableState {}
    interface TableOptionsResolved<TData extends RowData> extends RowEditingOptions<TData> {}
    interface Table<TData extends RowData> extends RowEditingInstance<TData> {}
    interface Row<TData extends RowData> extends RowEditingRow<TData> {}
    interface Cell<TData extends RowData, TValue> extends RowEditingCell<TData, TValue> {}
}
