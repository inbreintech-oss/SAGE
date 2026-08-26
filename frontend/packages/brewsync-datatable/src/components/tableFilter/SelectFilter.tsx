import React from "react";
import {FilterBaseProps} from "./FilterBase";
import FilterWrap from "./FilterWrap";
import {Select} from "@mantine/core";

export type SelectFilterProps = {
    options?: string[];
} & FilterBaseProps

export default function SelectFilter({
    ref,
    value,
    options,
    onSubmit,
    onDismiss,
}: SelectFilterProps) {
    const [filterOption, setFilterOptions] = React.useState<string | null>(value || null);

    return (
        <FilterWrap onSubmit={() => onSubmit?.(filterOption ?? "")}
                    onCancel={onDismiss}
                    onClear={() => onSubmit?.("")}
                    buttonsFirst
        >
            <Select ref={ref}
                    value={filterOption}
                    data={options || []}
                    size="xs"
                    onChange={(value) => setFilterOptions(value)}
                    comboboxProps={{withinPortal: false}}
                    allowDeselect
                    searchable
                    data-autofocus
            />
        </FilterWrap>
    )
}
