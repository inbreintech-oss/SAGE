import { Cell, RowData, Table } from "@tanstack/react-table";
import { TableCell } from "@/components";
import { MultiSelect, Combobox, Input, Loader, useCombobox } from "@mantine/core";
import { DensityState } from "@/features/density";
import { useEffect, useMemo, useState } from "react";

export type CodePickerEditingCellProps<TData extends RowData> = {
    table: Table<TData>;
    cell: Cell<TData, string | string[]>;
    density: DensityState;

    // CodePicker 설정
    codeGroupId: string;
    companyAppId: number;
    mode: "code" | "codeHelp";
    multiple?: boolean;

    // codeHelp 전용 옵션
    codeColumnId?: string;
    valueColumnId?: string;

    // ReactQuery 결과
    query?: {
        data?: { items?: Array<Record<string, unknown>> };
        isLoading?: boolean;
        isFetching?: boolean;
    };

    // 고정 목록 데이터
    data?: Array<Record<string, unknown>>;

    // 라벨 해결 함수
    resolveLabel?: (item: Record<string, unknown>) => string;

    // 값 접근 함수
    getCellValue?: (columnId: string, defaultValue: any) => any;
    updateCellValue?: (columnId: string, value: any) => void;
};

export default function CodePickerEditingCell<TData extends RowData>({
    table,
    cell,
    density,
    codeGroupId,
    companyAppId,
    mode = "code",
    multiple = false,
    codeColumnId,
    valueColumnId,
    query,
    data: fixedData,
    resolveLabel,
    getCellValue,
    updateCellValue,
}: CodePickerEditingCellProps<TData>) {
    const error = cell.getEditingError();
    const items = fixedData || query?.data?.items || [];
    const isLoading = query?.isLoading || false;
    const combobox = useCombobox({
        onDropdownClose: () => combobox.resetSelectedOption()
    });

    // 라벨 해결 함수 기본값
    const defaultResolveLabel = useMemo(() => {
        if (resolveLabel) return resolveLabel;

        if (mode === "code") {
            return (item: Record<string, unknown>) =>
                (item.korCodeName as string) || "";
        } else {
            return (item: Record<string, unknown>) =>
                String(item[valueColumnId!] || "");
        }
    }, [resolveLabel, mode, valueColumnId]);

    // 초기값 가져오기
    const initialValue = getCellValue
        ? getCellValue(cell.column.id, cell.getValue())
        : (cell.getEditingValue() as string | string[]) ?? (multiple ? [] : "");

    const [value, setValue] = useState<string | string[]>(initialValue);
    const [search, setSearch] = useState<string>("");
    const [isSearching, setIsSearching] = useState(false);

    // 코드 ID 추출 함수
    const getCodeId = (item: Record<string, unknown>): string => {
        if (mode === "code") {
            return String(item.codeId);
        } else {
            return String(item[codeColumnId!]);
        }
    };

    // 검색 필터링
    const filtered = useMemo(() => {
        const q = search.trim().toLowerCase();
        if (!q) {
            return items;
        }
        return items.filter((item) => {
            const id = getCodeId(item);
            const name = defaultResolveLabel(item).toLowerCase();
            return id.includes(q) || name.includes(q);
        });
    }, [items, search, getCodeId, defaultResolveLabel]);

    // 값 변경 시 라벨 동기화 (단일 선택만, 검색 중이 아닐 때만)
    useEffect(() => {
        if (multiple || isSearching) {
            return;
        }

        if (!value) {
            setSearch("");
            return;
        }

        // value가 codeColumnId 값인지 valueColumnId 값인지 확인하여 아이템 찾기
        let found = items.find(x => getCodeId(x) === value);
        
        // 못 찾았고, codeHelp 모드이며 valueColumnId가 있다면 valueColumnId로 다시 찾기
        if (!found && mode === "codeHelp" && valueColumnId) {
            found = items.find(x => String(x[valueColumnId] || "") === String(value));
            if (found) {
                // valueColumnId로 찾았다면 로컬 value를 codeColumnId 값으로 업데이트 (UI 동기화)
                setValue(getCodeId(found));
            }
        }

        if (found) {
            setSearch(defaultResolveLabel(found));
        }
    }, [value, items, multiple, defaultResolveLabel, getCodeId, isSearching, mode, valueColumnId]);

    const handleChange = (newValue: string | string[] | null) => {
        const finalValue = newValue ?? (multiple ? [] : "");
        setValue(finalValue);
        setIsSearching(false);

        // ref 업데이트 (리렌더 없음)
        if (updateCellValue) {
            // valueColumnId가 있으면 해당 값을 메인 값으로 사용
            if (mode === "codeHelp" && valueColumnId && !multiple && typeof finalValue === "string") {
                const found = items.find(x => getCodeId(x) === finalValue);
                if (found) {
                    updateCellValue(cell.column.id, found[valueColumnId]);
                    // 메인 컬럼 외에 valueColumnId 컬럼도 명시적으로 업데이트 (필요한 경우)
                    if (cell.column.id !== valueColumnId) {
                        updateCellValue(valueColumnId, found[valueColumnId]);
                    }
                } else if (!finalValue) {
                    updateCellValue(cell.column.id, null);
                    if (cell.column.id !== valueColumnId) {
                        updateCellValue(valueColumnId, null);
                    }
                }
            } else {
                updateCellValue(cell.column.id, finalValue);
            }
        }

        // 단일 선택 시 라벨 업데이트
        if (!multiple && typeof finalValue === "string") {
            const found = items.find(x => getCodeId(x) === finalValue);
            setSearch(found ? defaultResolveLabel(found) : finalValue);
            combobox.closeDropdown();
        }
    };

    const handleClear = () => {
        handleChange(multiple ? [] : null);
        setSearch("");
        combobox.closeDropdown();
    };

    // 다중 선택
    if (multiple) {
        const selectedValues = Array.isArray(value) ? value : [];
        const data = items.map(item => ({
            value: getCodeId(item),
            label: defaultResolveLabel(item)
        }));

        return (
            <TableCell width={cell.column.getSize()} px={0} py={0}>
                <MultiSelect
                    w="100%"
                    size={density}
                    value={selectedValues}
                    onChange={(v) => handleChange(v)}
                    data={data}
                    searchable
                    clearable
                    comboboxProps={{ withinPortal: true }}
                    rightSectionPointerEvents={isLoading ? "none" : "all"}
                    error={error}
                    styles={{
                        root: { height: "100%" },
                        wrapper: { height: "100%" },
                        input: {
                            height: "100%",
                            minHeight: 0,
                            borderRadius: 0,
                            border: error ? "1px solid red" : "none"
                        }
                    }}
                    rightSection={isLoading ? <Loader size="xs" /> : undefined}
                />
            </TableCell>
        );
    }

    // 단일 선택
    const options = filtered.map(item => {
        const code = getCodeId(item);
        return (
            <Combobox.Option value={code} key={code}>
                {defaultResolveLabel(item)}
            </Combobox.Option>
        );
    });

    return (
        <TableCell width={cell.column.getSize()} px={0} py={0}>
            <Combobox
                store={combobox}
                onOptionSubmit={(val) => handleChange(val)}
                withinPortal={true}
            >
                <Combobox.Target>
                    <Input
                        size={density}
                        value={search}
                        onChange={(e) => {
                            setSearch(e.currentTarget.value);
                            setIsSearching(true);
                            combobox.openDropdown();
                        }}
                        onClick={() => {
                            combobox.openDropdown();
                        }}
                        onFocus={() => {
                            combobox.openDropdown();
                        }}
                        onBlur={() => {
                            setTimeout(() => setIsSearching(false), 200);
                        }}
                        error={error}
                        rightSectionPointerEvents={isLoading ? "none" : "all"}
                        rightSection={isLoading ? (
                            <Loader size="xs" />
                        ) : value ? (
                            <span
                                style={{ cursor: "pointer", userSelect: "none" }}
                                onMouseDown={(e) => e.preventDefault()}
                                onClick={handleClear}
                                aria-label="clear"
                            >
                                ×
                            </span>
                        ) : (
                            <span style={{ display: "flex", alignItems: "center", paddingRight: "4px" }}>
                                <Combobox.Chevron />
                            </span>
                        )}
                        styles={{
                            wrapper: { height: "100%" },
                            section: { pointerEvents: (isLoading || (!value && !isLoading)) ? "none" : "all" },
                            input: {
                                height: "100%",
                                minHeight: 0,
                                borderRadius: 0,
                                border: error ? "1px solid red" : "none"
                            }
                        }}
                    />
                </Combobox.Target>
                <Combobox.Dropdown>
                    <Combobox.Options>
                        {options.length > 0 ? options : (
                            <Combobox.Empty>검색 결과가 없습니다</Combobox.Empty>
                        )}
                    </Combobox.Options>
                </Combobox.Dropdown>
            </Combobox>
        </TableCell>
    );
}
