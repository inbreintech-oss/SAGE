import dayjs from "dayjs";
import type {
    BooleanFormatOptions,
    CellFormatOptions,
    CodePickerFormatOptions,
    DateFormatOptions,
    NumericFormatOptions, SelectFormatOptions
} from "@/types";

/**
 * 숫자 포맷팅 함수
 */
function formatNumeric(value: any, options: NumericFormatOptions): string {
    const numValue = typeof value === 'number' ? value : parseFloat(value);
    
    if (isNaN(numValue)) {
        return String(value);
    }

    const {
        useGrouping = true,
        currencySymbol,
        maximumFractionDigits = 0,
        minimumFractionDigits = 0,
    } = options;

    const formatted = numValue.toLocaleString('ko-KR', {
        useGrouping,
        maximumFractionDigits,
        minimumFractionDigits,
    });

    if (currencySymbol) {
        return `${currencySymbol}${formatted}`;
    }

    return formatted;
}

/**
 * 날짜 포맷팅 함수
 */
function formatDate(value: any, options: DateFormatOptions): string {
    const {format = "YYYY-MM-DD"} = options;

    if (!value) {
        return '';
    }

    const date = dayjs(value);

    if (!date.isValid()) {
        return String(value);
    }

    return date.format(format);
}

/**
 * Boolean 포맷팅 함수
 */
function formatBoolean(value: any, options: BooleanFormatOptions): string {
    const {
        trueLabel = "Yes",
        falseLabel = "No",
    } = options;

    // Boolean 타입 또는 boolean 문자열 처리
    if (typeof value === 'boolean') {
        return value ? trueLabel : falseLabel;
    }

    // 문자열 "true"/"false" 처리
    if (typeof value === 'string') {
        const lowerValue = value.toLowerCase();
        if (lowerValue === 'true') return trueLabel;
        if (lowerValue === 'false') return falseLabel;
    }

    // 숫자 1/0 처리
    if (typeof value === 'number') {
        return value ? trueLabel : falseLabel;
    }

    return Boolean(value) ? trueLabel : falseLabel;
}

/**
 * Select 포맷팅 함수
 */
function formatSelect(value: any, options: SelectFormatOptions): string {
    const option = options.options.find(opt => opt.value === String(value));
    return option ? option.label : String(value);
}

/**
 * CodePicker 포맷팅 함수
 */
function formatCodePicker(value: any, options: CodePickerFormatOptions): string {
    if (value === undefined || value === null || value === "") {
        return "";
    }

    const items = options.data || options.query?.data?.items || [];
    const mode = options.mode || "code";
    const codeColumnId = options.codeColumnId;
    const valueColumnId = options.valueColumnId;

    const getCodeId = (item: Record<string, unknown>): string => {
        if (mode === "code") {
            return String(item.codeId);
        } else {
            return String(item[codeColumnId!]);
        }
    };

    const resolveLabel = options.resolveLabel || ((item: Record<string, unknown>) => {
        if (mode === "code") {
            return (item.korCodeName as string) || "";
        } else {
            return String(item[valueColumnId!] || "");
        }
    });

    if (options.multiple && Array.isArray(value)) {
        return value.map(v => {
            const item = items.find(i => getCodeId(i) === String(v));
            return item ? resolveLabel(item) : String(v);
        }).join(", ");
    }

    const item = items.find(i => getCodeId(i) === String(value));
    
    // codeHelp 모드에서는 valueColumnId와 비교해서도 찾아봄 (UI 일관성)
    if (!item && mode === "codeHelp" && valueColumnId) {
        const foundByValue = items.find(i => String(i[valueColumnId] || "") === String(value));
        if (foundByValue) return resolveLabel(foundByValue);
    }

    return item ? resolveLabel(item) : String(value);
}

/**
 * 셀 값 포맷팅 메인 함수
 */
export function formatCellValue(value: any, options?: CellFormatOptions): string {
    if (value === undefined || value === null) {
        return "";
    }

    if (!options) {
        return String(value);
    }

    switch (options.type) {
        case "numeric":
            return formatNumeric(value, options);
        case "date":
            return formatDate(value, options);
        case "boolean":
            return formatBoolean(value, options);
        case "select":
            return formatSelect(value, options);
        case "codePicker":
            return formatCodePicker(value, options);
        default:
            return String(value);
    }
}
