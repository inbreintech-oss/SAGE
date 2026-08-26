import {useEffect, useMemo, useState} from "react";
import {
    useReactTable,
    getCoreRowModel,
    getFilteredRowModel,
    RowData,
    PaginationState,
    ColumnFiltersState,
    ColumnOrderState,
    VisibilityState,
    RowSelectionState,
    ColumnPinningState,
    RowPinningState,
    SortingState,
    ExpandedState,
    GroupingState,
    ColumnSizingInfoState,
    ColumnSizingState, TableState, ColumnDef, TableOptions
} from "@tanstack/react-table";
import {BrewSyncTableInstance, BrewSyncTableOptions} from "@/types";
import {DensityFeature, DensityState} from "@/features/density";
import {useSelectionColumn} from "@/hooks/columns/useSelectionColumn";
import {RowEditingState, RowEditing} from "@/features/rowEditing";
import {useEditActionColumn} from "@/hooks/columns/useEditActionColumn";
import {RowClick} from "@/features/rowClick";

/**
 * DataTable Instance를 생성하여 반환합니다.
 */
export function useDataTable<TData extends RowData>(options: BrewSyncTableOptions<TData>): BrewSyncTableInstance<TData> {
    const initialState = useMemo<Partial<TableState>>(() => {
        const state = options.initialState ?? {};
        const enableDeleteVal = options.enableDelete ?? options.meta?.enableDelete ?? true;

        if (!state.columnVisibility) {
            state.columnVisibility = {}
        }

        state.columnVisibility["__delete_action_column__"] = enableDeleteVal;

        options.columns.forEach(column => {
            if (!column.id) {
                return;
            }
            state.columnVisibility![column.id] = column.visibility ?? true;
        });

        return state;
    }, []);


    // Default State Initialize
    const [internalColumnPinning, setInternalColumnPinning] = useState<ColumnPinningState>(initialState?.columnPinning ?? {});
    const [internalRowPinning, setInternalRowPinning] = useState<RowPinningState>(initialState?.rowPinning ?? {});
    const [internalGlobalFilter, setInternalGlobalFilter] = useState<string>(initialState?.globalFilter ?? "");
    const [internalSorting, setInternalSorting] = useState<SortingState>(initialState?.sorting ?? []);
    const [internalExpanded, setInternalExpanded] = useState<ExpandedState>(initialState?.expanded ?? {});
    const [internalGrouping, setInternalGrouping] = useState<GroupingState>(initialState?.grouping ?? []);
    const [internalColumnSizing, setInternalColumnSizing] = useState<ColumnSizingState>(initialState?.columnSizing ?? {});
    const [internalColumnSizingInfo, setInternalColumnSizingInfo] = useState<ColumnSizingInfoState>(initialState?.columnSizingInfo ?? ({} as ColumnSizingInfoState));
    const [internalColumnFilters, setInternalColumnFilters] = useState<ColumnFiltersState>(initialState?.columnFilters ?? []);
    const [internalColumnOrder, setInternalColumnOrder] = useState<ColumnOrderState>(initialState?.columnOrder ?? []);
    const [internalColumnVisibility, setInternalColumnVisibility] = useState<VisibilityState>(initialState?.columnVisibility ?? {});
    const [internalRowSelection, setInternalRowSelection] = useState<RowSelectionState>(initialState?.rowSelection ?? {});
    const [internalPagination, setInternalPagination] = useState<PaginationState>(
        {
            pageIndex: 0,
            pageSize: 25,
            ...initialState?.pagination
        }
    );

    // Custom Feature States
    const [internalDensity, setInternalDensity] = useState<DensityState>(initialState?.density ?? "sm");
    const [internalEditingRows, setInternalEditingRows] = useState<RowEditingState>(initialState?.rowEditing ?? {});

    // Use provided state from options or fall back to internal state
    const columnPinning = options.state?.columnPinning ?? internalColumnPinning;
    const rowPinning = options.state?.rowPinning ?? internalRowPinning;
    const globalFilter = options.state?.globalFilter ?? internalGlobalFilter;
    const sorting = options.state?.sorting ?? internalSorting;
    const expanded = options.state?.expanded ?? internalExpanded;
    const grouping = options.state?.grouping ?? internalGrouping;
    const columnSizing = options.state?.columnSizing ?? internalColumnSizing;
    const columnSizingInfo = options.state?.columnSizingInfo ?? internalColumnSizingInfo;
    const columnFilters = options.state?.columnFilters ?? internalColumnFilters;
    const columnOrder = options.state?.columnOrder ?? internalColumnOrder;
    const columnVisibility = options.state?.columnVisibility ?? internalColumnVisibility;
    const rowSelection = options.state?.rowSelection ?? internalRowSelection;
    const pagination = options.state?.pagination ?? internalPagination;
    const density = options.state?.density ?? internalDensity;
    const editingRows = options.state?.rowEditing ?? internalEditingRows;

    // 에디팅 상태에 따른 컬럼 가시성 자동 조절
    const isEditing = Object.keys(editingRows).length > 0;
    const enableDelete = options.enableDelete ?? options.meta?.enableDelete ?? true;

    useEffect(() => {
        setInternalColumnVisibility(prev => {
            const next = { ...prev };
            next["__edit_action_column__"] = !isEditing;
            next["__delete_action_column__"] = enableDelete && !isEditing;
            next["__save_action_column__"] = isEditing;
            
            // 변경사항이 있는 경우에만 업데이트하여 무한 루프 방지
            const isChanged = next["__edit_action_column__"] !== prev["__edit_action_column__"] ||
                next["__delete_action_column__"] !== prev["__delete_action_column__"] ||
                next["__save_action_column__"] !== prev["__save_action_column__"];

            if (!isChanged) return prev;
            return next;
        });
    }, [isEditing, enableDelete]);


    // Initialize ColumnDefs
    const columnDefs = useMemo(() => {
        // BrewSyncColumnDef의 상위 레벨 옵션을 meta로 매핑
        const mappedColumns = options.columns.map(col => {
            const { headerAlign, contentAlign, cellFormat, enableEditing, editingConfig, meta, ...rest } = col;

            return {
                ...rest,
                meta: {
                    ...meta,
                    ...(headerAlign !== undefined && { headerAlign }),
                    ...(contentAlign !== undefined && { contentAlign }),
                    ...(cellFormat !== undefined && { cellFormat }),
                    ...(enableEditing !== undefined && { enableEditing }),
                    ...(editingConfig !== undefined && { editingConfig }),
                }
            } as ColumnDef<TData>;
        });

        const rdtOptionsForColumns = {
            ...options,
            state: {
                columnSizingInfo,
                rowEditing: editingRows,
                sorting,
                expanded,
                columnFilters,
                columnOrder,
                columnVisibility,
                rowSelection,
                pagination,
                columnPinning,
                rowPinning,
                grouping,
                columnSizing,
                density,
                globalFilter,
            }
        } as TableOptions<TData>;

        return [
            // RowSelection Column
            ...([
                options.enableRowSelection && useSelectionColumn(rdtOptionsForColumns),
            ].filter(Boolean) as ColumnDef<TData>[]),
            ...mappedColumns,
            ...([
                options.enableRowEditing && useEditActionColumn(rdtOptionsForColumns),
            ].filter(Boolean).flat() as ColumnDef<TData>[]),
        ];
    }, [
        options.columns,
        options.enableRowSelection,
        options.enableRowEditing,
        // rdtOptions의 state 요소들
        columnSizingInfo, editingRows, sorting, expanded, columnFilters, columnOrder,
        columnVisibility, rowSelection, pagination, columnPinning, rowPinning,
        grouping, columnSizing, density, globalFilter
    ]);

    return useReactTable({
        _features: [DensityFeature, RowEditing, RowClick],
        ...options,
        state: {
            columnSizingInfo,
            rowEditing: editingRows,
            sorting,
            expanded,
            columnFilters,
            columnOrder,
            columnVisibility,
            rowSelection,
            pagination,
            columnPinning,
            rowPinning,
            grouping,
            columnSizing,
            density,
            globalFilter,
        },
        columns: columnDefs,
        getCoreRowModel: getCoreRowModel(),
        getFilteredRowModel: getFilteredRowModel(),
        onColumnFiltersChange: options.onColumnFiltersChange ?? setInternalColumnFilters,
        onColumnOrderChange: options.onColumnOrderChange ?? setInternalColumnOrder,
        onColumnVisibilityChange: options.onColumnVisibilityChange ?? setInternalColumnVisibility,
        onRowSelectionChange: options.onRowSelectionChange ?? setInternalRowSelection,
        onPaginationChange: options.onPaginationChange ?? setInternalPagination,
        onSortingChange: options.onSortingChange ?? setInternalSorting,
        onRowPinningChange: options.onRowPinningChange ?? setInternalRowPinning,
        onColumnPinningChange: options.onColumnPinningChange ?? setInternalColumnPinning,
        onColumnSizingChange: options.onColumnSizingChange ?? setInternalColumnSizing,
        onColumnSizingInfoChange: options.onColumnSizingInfoChange ?? setInternalColumnSizingInfo,
        onExpandedChange: options.onExpandedChange ?? setInternalExpanded,
        onGroupingChange: options.onGroupingChange ?? setInternalGrouping,
        onGlobalFilterChange: options.onGlobalFilterChange ?? setInternalGlobalFilter,
        onDensityChanged: options.onDensityChanged ?? setInternalDensity,
        onRowEditingChanged: options.onRowEditingChanged ?? setInternalEditingRows
    }) as BrewSyncTableInstance<TData>;
}
